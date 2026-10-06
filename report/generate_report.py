"""Rebuild the final report from recorded runs, without calling a model."""
import json
import re
import subprocess
from pathlib import Path

from lab.compare import ORDER, build_table, load_runs
from lab.curator import validate_skill
from lab.tasks import ROOT


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def md_table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
        *("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |" for row in rows),
    ])


def main():
    runs = load_runs(ROOT / "results")
    assert len(runs) == 18, "Finish all 18 official runs before generating the report."
    indexed = {(r["condition"], r["task"]): r for r in runs}
    comparison = build_table(runs)
    (ROOT / "report/table.md").write_text(comparison + "\n", encoding="utf-8")
    breakdown = subprocess.check_output(["python", "scripts/check_breakdown.py"], cwd=ROOT, text=True).strip()
    (ROOT / "report/check_breakdown.txt").write_text(breakdown + "\n", encoding="utf-8")
    verification = subprocess.check_output(["python", "scripts/verify_freeze.py"], cwd=ROOT, text=True).strip()
    freeze = git("rev-parse", "freeze")
    hyp_commit = git("log", "freeze", "--format=%H", "--grep=^hypotheses").splitlines()[0]
    preregistration = git("show", f"{hyp_commit}:report/REPORT.md")
    hypotheses = "\n".join(line for line in preregistration.splitlines() if line.startswith(("- H1", "- H2", "- H3")))
    assert len(hypotheses.splitlines()) == 3

    failure_rows = []
    for task in ("code-learn", "data-learn", "logs-learn"):
        for check in indexed["baseline", task]["checks"]:
            if not check["passed"]:
                group = "E" if check["name"].startswith("rule_") else "D (kèm dấu hiệu A/B trong vết)"
                failure_rows.append([task, check["name"], group, check.get("detail", "")])
    taxonomy = md_table(["Tác vụ", "Check thất bại", "Nhóm", "Bằng chứng từ detail"], failure_rows)

    delegation_rows = []
    for task in sorted(r["task"] for r in runs if r["condition"] == "subagents"):
        run = indexed["subagents", task]
        baseline = indexed["baseline", task]
        trace = (ROOT / "results/subagents" / task / "trace.md").read_text(encoding="utf-8")
        names = re.findall(r'"subagent_type":\s*"([^"\n]+)"', trace)
        delegation_rows.append([task, run["subagent_calls"], ", ".join(names) or "Không thấy tên trong vết", baseline["tokens"]["total"], run["tokens"]["total"], baseline["seconds"], run["seconds"]])
    delegation = md_table(["Task", "task calls", "Subagent", "Token baseline", "Token subagents", "Giây baseline", "Giây subagents"], delegation_rows)

    skill_rows = []
    for path in sorted((ROOT / "skills/auto").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        assert not validate_skill(text, expected_name=path.parent.name)
        body = text.split("---", 2)[2].strip()
        if "python" in path.parent.name:
            judgment = "Tổng quát cho sửa package Python; bao phủ type hints, regression tests và changelog đúng feedback. Điều kiện tối thiểu ba test/bullet chỉ áp dụng khi sửa ba lỗi trở lên có thể bỏ sót quy ước trong tác vụ ít lỗi. Tên file output và heading là quy ước, không phải đáp án."
            trigger = "Viết/cập nhật package Python; description đúng phạm vi."
        else:
            judgment = "Tổng quát cho log nhiều dòng, timezone và repeat; giữ đúng quy ước tên service và schema. 'Immediately follow' có thể gây hiểu sai nếu repeat ở sau traceback. Sơ đồ top-level thiếu counts_by_service dù bước 8 yêu cầu tổng hợp; không buộc dùng parser chương trình."
            trigger = "Phân tích log với repeat, timestamp và exception; description đủ rộng."
        skill_rows.append([path.parent.name, judgment, f"{len(text.splitlines())} dòng toàn file / {len(body.splitlines())} dòng body. {trigger}"])
    skills = md_table(["Skill", "Tính tổng quát và đúng/sai", "Độ dài, description"], skill_rows)

    costs = []
    stats = {}
    for condition in ORDER:
        for role in ("learn", "eval"):
            selected = [r for r in runs if r["condition"] == condition and r["role"] == role]
            score = sum(r["score"] for r in selected) / len(selected)
            tokens = sum(r["tokens"]["total"] for r in selected) / len(selected)
            seconds = sum(r["seconds"] for r in selected) / len(selected)
            stats[condition, role] = (score, tokens, seconds)
            costs.append([condition, role, f"{score:.4f}", f"{tokens:,.1f}", f"{seconds:.1f}", f"{score / tokens * 100000:.3f}"])
    cost_table = md_table(["Condition", "Role", "Mean score", "Mean tokens", "Mean seconds", "Tổng score / 100k token"], costs)

    noise_rows = []
    for task in ("code-learn", "data-learn", "logs-learn"):
        dev = json.loads((ROOT / "results/skills-auto-dev" / task / "run.json").read_text(encoding="utf-8"))
        official = indexed["skills-auto", task]
        assert dev["skills_sha256"] == official["skills_sha256"]
        noise_rows.append([task, f"{dev['passed']}/{dev['total']}", f"{official['passed']}/{official['total']}", f"{official['score'] - dev['score']:+.4f}", dev["tokens"]["total"], official["tokens"]["total"], dev["skills_read"], official["skills_read"]])
    noise = md_table(["Task", "Phần 3.4", "Sau freeze", "Delta score", "Token dev", "Token chính thức", "Skill read dev", "Skill read chính thức"], noise_rows)

    new_rules = []
    for family in ("code", "data", "logs"):
        learned = {c["name"] for c in indexed["baseline", f"{family}-learn"]["checks"]}
        official = indexed["skills-auto", f"{family}-eval"]
        for check in official["checks"]:
            if check["name"].startswith("rule_") and check["name"] not in learned:
                new_rules.append([official["task"], check["name"], "Đạt" if check["passed"] else "Không đạt", official["skills_read"]])
    new_rule_table = md_table(["Task đánh giá", "Quy ước mới (tên check)", "skills-auto", "skills_read"], new_rules)
    errors = [f"{r['condition']}/{r['task']}: {r['error']}" for r in runs if r.get("error")]
    modified = [f"{r['condition']}/{r['task']}" for r in runs if r["skills_modified"]]
    skill_read = sum(r["skills_read"] > 0 for r in runs if r["condition"] == "skills-auto")
    all_records = list((ROOT / "results").rglob("run.json"))
    api_failures = list((ROOT / "results/infrastructure-api").rglob("run.json"))
    total_tokens = sum(json.loads(p.read_text(encoding="utf-8"))["tokens"]["total"] for p in all_records)
    baseline_learn = stats["baseline", "learn"][0]
    baseline_eval = stats["baseline", "eval"][0]
    changes = "\n".join(
        f"- {condition}: mean học {stats[condition, 'learn'][0]:.4f} (delta {stats[condition, 'learn'][0] - baseline_learn:+.4f}), "
        f"mean đánh giá {stats[condition, 'eval'][0]:.4f} (delta {stats[condition, 'eval'][0] - baseline_eval:+.4f})."
        for condition in ("subagents", "skills-auto")
    )
    best = max(ORDER, key=lambda c: stats[c, "eval"][0] / stats[c, "eval"][1])
    h1 = stats["subagents", "eval"][0] <= baseline_eval and stats["subagents", "eval"][1] > stats["baseline", "eval"][1]
    h2 = abs(stats["skills-auto", "eval"][0] - baseline_eval) <= 0.10

    report = f"""# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Đàm Việt Hưng | 2A202602600 | Harness, thí nghiệm, phân tích báo cáo; có hỗ trợ của Codex |

Tên/mã lấy từ tên kho và cần đối chiếu trước khi nộp. Mô hình `gpt-4.1-mini`, nhiệt độ 0, recursion limit 60; dùng OpenAI-compatible endpoint qua cấu hình có sẵn của lab.model. Python 3.12.15, Deep Agents 0.7.21, Linux trong Docker Desktop trên Windows/WSL2. Phiên bản đầy đủ: [environment.json](environment.json), [dependencies.txt](dependencies.txt).

29/29 test ngoại tuyến đạt trong Docker. Windows trực tiếp đạt 27/29; hai lỗi do thiếu lệnh Unix, đúng yêu cầu môi trường trong README. Tổng {len(all_records)} lần chạy task: 18 chính thức, 3 dev với bộ skill cuối, 3 với bộ skill đầu, 2 code bị ảnh hưởng CRLF và {len(api_failures)} lần lỗi kết nối API bị loại. Hai lần gọi curator, một kết nối mô hình nhỏ; ngân sách task không được nêu trong kho. Tổng token task đã ghi: {total_tokens:,}; chưa bao gồm curator và kiểm tra kết nối vì chúng không có usage record. Không giả định ngân sách còn lại hay chi phí tiền.

Commit hypotheses: `{hyp_commit}`. Tag freeze: `{freeze}`. `.env` bị Git bỏ qua; khóa không xuất hiện trong kết quả/báo cáo. .gitattributes giữ LF cho task và skill để checkout Windows không làm sai hash gốc. Không thay đổi nội dung tệp task/tests/scripts hay các module được cung cấp.

## 2. Giả thuyết (đã commit trước tag freeze)

Các dòng dưới giữ nguyên dự đoán trong commit hypotheses; không điều chỉnh theo kết quả đánh giá.

{hypotheses}

## 3. Làm quen Deep Agents

1. [tour.txt](tour.txt) liệt kê ls, read_file, write_file, edit_file, delete, glob, grep, execute, task. execute chạy shell; task giao việc cho subagent.
2. general-purpose có cùng công cụ với tác tử chính. Mỗi lần gọi mặc định độc lập, chỉ nhận prompt giao việc và trả về báo cáo cuối; không tự thấy toàn bộ ngữ cảnh của tác tử chính. Cần gửi đủ quy tắc và đường dẫn.
3. Trích task: “Each invocation is stateless by default”. Trích execute: “Quote paths containing spaces”. System prompt của tour rỗng, nhưng mô tả công cụ vẫn hướng dẫn hành vi. Harness sử dụng nguyên BASE_PROMPT đã cho; đường dẫn workspace/... tương đối dùng chung được cho công cụ tệp và shell.

## 4. Đường cơ sở và phân loại lỗi

Chỉ dùng baseline học hợp lệ. Mỗi dòng sau là một check thất bại thực tế; các quy tắc trong detail là phản hồi học, không phải đáp án đánh giá.

{taxonomy}

Nhóm E chiếm 9/14 check thất bại (64,3%). Năm lỗi kỹ thuật còn lại thuộc logs, có dấu hiệu A/B đi kèm: vết baseline logs không đọc README và không chạy parser/test, viết trực tiếp JSON bằng write_file; timestamp offset bị viết thành Z mà không chuyển đúng giờ, thiếu bản ghi và sai traceback/repeat. Skill có thể nhắc quy trình và quy ước, nhưng phải được đọc và thực thi.

Bằng chứng phủ định có phạm vi: code đạt 7/7 check kỹ thuật, đọc docstring, sửa hàm dùng chung và chạy test; data đạt 5/5 check tính toán. Tổng kỹ thuật 13/18, quy ước 0/9. Không suy diễn rằng A–D không xảy ra ở mọi task; logs chỉ đạt 1/6 kỹ thuật. Không có bằng chứng baseline báo đã tạo file nhưng file không tồn tại, nên không gán F chỉ vì câu kết thúc chung chung.

Hai code baseline đầu có tests_not_modified thất bại do CRLF checkout, không do agent sửa test. Hash checkout efb5e765… khác Git 79e05f4c… đúng hash của checker; hai byte stream chỉ khác line ending. Lệnh checkout-index ban đầu không viết lại file vì Git xem nội dung đã tương đương; sau đó khôi phục chính xác byte từ Git cho task. Hai run được giữ ở results/infrastructure-crlf và loại khỏi so sánh/curator. Không thay đổi nội dung gốc của task. Baseline code hợp lệ sau đó đạt check tests_not_modified.

## 5. Điều kiện subagents

Explorer đọc tài liệu/tìm nguyên nhân, implementer thực hiện và kiểm chứng, reviewer kiểm tra độc lập. Description nêu khi nào giao việc, system prompt phân định phạm vi; build_agent nối PATHS_NOTE cho từng subagent.

{delegation}

Data-learn giao việc cho implementer. Lời giao có chỉ tiêu, sentinel, định dạng ngày và đường dẫn answer.json, nhưng đường dẫn input/README chưa đầy đủ và quy ước Acme chưa thành yêu cầu cụ thể. Tác tử chính nhận báo cáo với các số liệu rồi write_file ngay; không chạy script đối chiếu, cả năm check tính toán sai. Vết chỉ có luồng chính, nên không khẳng định chính xác cách implementer tính bên trong.

Ở các run không có task call, việc chọn tự làm là kết quả hợp lệ. Không thể biết chắc động cơ nội bộ; một khả năng là mô hình coi phạm vi đủ nhỏ. Trên tập học, token trung bình baseline 39.709 và subagents 54.263 (+36,7%), không đổi điểm code/logs và làm giảm điểm data. Token bao gồm subagent nhờ callback; số tool call chỉ tính luồng chính.

## 6. Self-evolving: skill do curator sinh

Curator chạy hai lần, chỉ đọc role=learn của baseline, bỏ qua run có lỗi hạ tầng. Lần đầu sinh ba skill; bộ đầu có ví dụ canonical region viết thường trái với feedback North/South/East/West, còn skill code yêu cầu commit/mypy ngoài phạm vi. Bộ này được bảo toàn nguyên trạng ở [curator-attempt-1/skills](curator-attempt-1/skills); kết quả kiểm tra ở results/skills-auto-attempt-1: 7/10, 5/8, 1/9, tất cả skills_read=0.

Chỉnh prompt curator để giữ chính xác casing/header/schema, phân bổ skill theo họ lỗi và tránh yêu cầu ngoài phạm vi, rồi sinh lại. Không sửa tay SKILL.md. Lần hai có hai skill hợp lệ. Skill data bị validator từ chối vì chứa marker orders, một danh từ chung cũng xuất hiện trong tên file đánh giá: đây có thể là false positive của bộ lọc substring, không chứng minh đọc dữ liệu đánh giá. Không sửa validator. Ba skill lần đầu được chuyển ra ngoài skills/auto, hai skill lần hai được giữ và đóng băng.

{skills}

Kết quả Phần 3.4 của bộ cuối: code 7/10, data 2/8, logs 1/9; sao lưu results/skills-auto-dev trước chạy chính thức. Bộ cuối thiếu skill data và không hứa giải quyết mọi lỗi. Trên sáu run chính thức, {skill_read}/6 có đọc skill theo định nghĩa read_file ở luồng chính. Xem bảng nhiễu ở mục 8 để đối chiếu với dev.

## 7. Kết quả so sánh

Bảng dưới do lab.compare sinh từ 18 run.json; bản độc lập ở [table.md](table.md).

{comparison}

Phân rã do scripts/check_breakdown.py:

```text
{breakdown}
```

Lỗi API/harness trong 18 run chính thức: {', '.join(errors) if errors else 'không có'}. skills_modified=true: {', '.join(modified) if modified else 'không có'}. Kiểm tra freeze trong Linux: `{verification}`. Hai run CRLF và {len(api_failures)} run lỗi kết nối API được giữ riêng ở results/infrastructure-crlf và results/infrastructure-api, không coi là thất bại tác tử. code-eval/skills-auto có lỗi OpenAIConnectionError với 0 token được chạy lại sau batch, không đổi skill. Mọi run skills-auto chính thức bắt đầu sau freeze, dùng đúng hash skill đã đóng băng.

## 8. Phân tích

### 8.1. Học và đánh giá

Baseline mean học {baseline_learn:.4f}, mean đánh giá {baseline_eval:.4f}.

{changes}

H1 {'phù hợp' if h1 else 'không được hỗ trợ đầy đủ'} với điểm/token đánh giá: điểm subagents thấp hơn, nhưng token đánh giá cũng thấp hơn (34.973 so với 44.211), trái với dự đoán chi phí cao hơn. H2 {'phù hợp' if h2 else 'không được hỗ trợ'} với ngưỡng chênh lệch đã đăng ký: delta đánh giá -0,0333. Không điều kiện nào cải thiện mean học hoặc đánh giá so với baseline; vì vậy không có mẫu cải thiện học nhưng giảm khả năng chuyển giao trong bộ chính thức này. H3 phụ thuộc skill thực sự được áp dụng; không đọc skill nên thí nghiệm chưa kiểm tra cơ chế chuyển giao nội dung, dù cả ba quy ước mới đều không đạt. Không dùng thay đổi nhỏ trên một run để kết luận khả năng tổng quát.

### 8.2. Kỹ thuật và quy ước

Dùng breakdown ở mục 7 để tách năng lực tính toán/sửa lỗi khỏi quy ước Acme. Trên tập học, skills-auto đạt 12/18 kỹ thuật so với baseline 13/18, cả hai 0/9 quy ước; mất check csv_quoting_follows_docstring trong code. Trên đánh giá, cả hai 13/18 kỹ thuật, nhưng baseline có 1/12 quy ước (rule_service_names ở logs-eval), còn skills-auto 0/12. Không có lợi ích quan sát được ở nhóm quy ước mà curator nhắm đến. Các check quy ước mới sau đây được xác định bằng tên check đánh giá không có ở họ học tương ứng, chỉ sau freeze:

{new_rule_table}

Không suy đoán đáp án hoặc điều kiện chính xác của check ẩn từ tên; feedback đánh giá được để trống theo grading.py. Bộ skill được sinh trước đánh giá và không chứa các định danh mới. Nếu skills_read=0, không thể gán việc đạt hoặc thất bại cho nội dung skill.

### 8.3. Cơ chế dùng skill

Không có đủ bằng chứng để nêu một check được skill giúp đạt nếu vết không có đọc skill. Ví dụ rule_type_hints ở code cho phép kiểm tra ý này: skill Python hướng dẫn thêm annotations, nhưng vết không đọc SKILL.md và code kết thúc sau sửa hành vi/chạy tests, nên quy ước vẫn thất bại. Logs cũng không đọc skill log; viết JSON trực tiếp nên những yêu cầu parser/repeat/schema không được đảm bảo. Những check kỹ thuật đã đạt ở baseline không được tính là lợi ích nhân quả của skill. Kết quả này cho thấy thất bại ở khâu lựa chọn/áp dụng skill, chưa chứng minh skill sẽ vô ích nếu được đọc đúng.

### 8.4. Chi phí

{cost_table}

Chỉ số hiệu suất là tổng điểm task chia tổng token, nhân 100.000; dùng để so sánh trong cùng tập này, không phải đơn vị chất lượng tuyệt đối. {best} có tỷ lệ điểm/token cao nhất trên đánh giá. Với các chênh lệch quan sát được, chưa có bằng chứng rằng chi phí đa tác tử mang lại lợi ích đủ chắc chắn. Điều kiện subagents đồng thời thêm prompt giao việc, nên ảnh hưởng không chỉ đến từ số task call.

### 8.5. Rò rỉ và quá khớp

Không đưa run/trace đánh giá vào curator. Kiểm thử ngoại tuyến theo hướng dẫn có sử dụng checker trên workspace chưa sửa; không dùng kết quả đó để thiết kế skill. Không đọc nội dung check.py đánh giá trước freeze. Phản hồi quy ước học được phép chứa tên output, heading và schema constants, không phải đáp án. Validator chặn marker đánh giá và tên chứa ../ trước khi tạo đường dẫn. Commit hypotheses đứng trước freeze; skill không đổi từ tag. Các kết quả dev/bộ cũ được tách khỏi 18 run chính thức để tránh trộn phiên bản. Không đủ bằng chứng kết luận quá khớp nội dung khi skill không được đọc; khác biệt học/đánh giá có thể do dữ liệu, lỗi parser và nhiễu.

### 8.6. Nhiễu cùng bộ skill

{noise}

Hai nhóm chạy dùng cùng hash skill. Code giảm 0,10; data tăng 0,375; logs không đổi. Vết code chính thức bỏ sót CSV quoting; vết data dev có lỗi xử lý offset âm trong parser, trong khi data chính thức đạt lại cả năm chỉ tiêu. Mean học của cùng bộ skill tăng từ 0,3537 ở dev lên 0,4454 (+0,0917); lớn hơn delta skills-auto so với baseline chính thức (-0,0333). Chênh lệch chỉ là hai mẫu dưới cùng cấu hình, không phải ước lượng phương sai đáng tin cậy. Nhiệt độ 0 không bảo đảm lặp lại hoàn toàn; các quyết định đọc file, viết script và xử lý timezone có thể thay đổi. Chênh lệch giữa điều kiện cần được diễn giải thận trọng. Không chọn run tốt nhất thay cho run chính thức.

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba task mỗi vai trò; một lỗi trong một họ làm thay đổi mạnh trung bình, không đại diện mọi công việc.
2. Một lần chạy chính thức mỗi task/condition; nhiễu và khoảng tin cậy chưa được đo bằng nhiều lần lặp độc lập.
3. Quy ước ẩn do giảng viên thiết kế; cải thiện nhờ feedback quy ước khác với cải thiện năng lực suy luận kỹ thuật chung.
4. Một mô hình/một harness; không suy rộng sang mô hình khác hay chiến lược giao việc khác. Không đọc skill gây khó tách chất lượng skill khỏi khả năng lựa chọn skill.
5. Vết cắt từng message ở 1.500 ký tự và không có bước nội bộ subagent. Khi invoke ném lỗi, cách cài đặt tối thiểu không giữ vết trung gian dù token callback vẫn có thể ghi chi phí.
6. LocalShellBackend cô lập bản sao workspace và làm sạch env, không tạo biên an ninh OS. Docker hạn chế tiếp cận host nhưng /lab được bind mount; không phù hợp để coi là sandbox bảo mật cho dữ liệu độc hại.
7. Bộ lọc substring có false positive tiềm năng ở danh từ orders, làm mất skill data và giảm bao phủ. Giữ nguyên bộ lọc theo quy định của lab.
8. Hash của tasks.hash_dir dùng biểu diễn đường dẫn của OS; đối chiếu freeze cần chạy cùng Linux/Docker như experiment. Việc Windows Git đổi CRLF đã được xử lý bằng nguyên byte Git và .gitattributes.
9. Kết nối mạng có gián đoạn: code-learn/skills-auto hoàn tất không có error nhưng mất 126,9 giây, có thể gồm chờ/retry API; không diễn giải toàn bộ thời gian này là chi phí suy luận. Run code-eval có lỗi đã được loại riêng và chạy lại.

## 10. Kết luận

Harness đạt 29/29 test và đã lưu đủ 18 kết quả chính thức cùng vết, giả thuyết trước freeze và hai skill do curator sinh. Các kết quả học cho thấy bỏ sót quy ước Acme và xử lý log là hai nguồn lỗi chính. Kết quả đánh giá chưa chứng minh lợi ích ổn định của đa tác tử hoặc skill tự sinh trong cấu hình này; việc không đọc skill giới hạn kết luận về chất lượng nội dung. Bước tiếp theo là đo lặp độc lập và nghiên cứu khả năng lựa chọn/áp dụng skill, giữ kết quả mở rộng tách khỏi bộ đã đóng băng.

## Phụ lục: tái lập

Không làm thử thách mở rộng. Để tái lập trong Linux, cài theo README, điền .env cục bộ; kiểm tra bằng `python -m pytest`, `python scripts/verify_freeze.py`, `python -m lab.compare`, `python scripts/check_breakdown.py`. Trên Windows dùng Docker, không chạy Unix shell tests trực tiếp bằng Python Windows. Với kho đã nộp, không tạo lại hay thay tag freeze; thí nghiệm mới nên ở clone/branch riêng và results riêng.

Chuỗi thí nghiệm đã thực hiện (các lệnh Python chạy qua docker exec deepagents-lab-day20):

```text
python -m pytest
python scripts/tour.py
python -m lab.runner --condition baseline --tasks learn
# Lưu hai code run CRLF riêng; khôi phục chính xác byte Git của task.
python -m lab.runner --condition subagents --tasks learn
python -m lab.runner --condition baseline --tasks code-learn
python -m lab.curator
python -m lab.runner --condition skills-auto --tasks learn
# Lưu skill/runs bộ đầu, cải thiện prompt curator (không sửa SKILL.md).
python -m lab.curator
python -m lab.runner --condition skills-auto --tasks learn
# Đổi results/skills-auto thành results/skills-auto-dev.
git commit -m hypotheses
git commit --allow-empty -m "freeze skills"
git tag freeze
python -m lab.runner --condition baseline --tasks eval
python -m lab.runner --condition subagents --tasks eval
python -m lab.runner --condition skills-auto --tasks all
# Lưu riêng code-eval có lỗi kết nối; chạy lại task này.
python -m lab.runner --condition skills-auto --tasks code-eval
python scripts/verify_freeze.py
python -m lab.compare
python scripts/check_breakdown.py
python report/generate_report.py
```

Docker: build bằng Dockerfile được cung cấp (`docker build -t lab-deepagents .`), chạy container với thư mục kho bind mount vào /lab. Cài git trong container bằng apt-get update và apt-get install -y --no-install-recommends git để chạy verify_freeze/check_breakdown. Danh sách package Python đã lưu giúp nhận biết dependency drift. report/generate_report.py chỉ đọc kết quả, giữ nguyên giả thuyết trong Git và sinh lại report/table, không gọi API hay thay skill.

Tài liệu tham khảo: [SkillsBench v1](https://arxiv.org/abs/2602.12670v1) cho nhận xét về skill tự sinh; [SkillEvolBench](https://arxiv.org/abs/2605.24117) cho giới hạn chuyển giao sau đóng băng. Không dùng kết quả nghiên cứu làm số liệu của lab.
"""
    (ROOT / "report/REPORT.md").write_text(report, encoding="utf-8")
    print(f"Generated report from {len(runs)} official runs; {verification}")


if __name__ == "__main__":
    main()
