"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {
            "name": "explorer",
            "description": "Delegate discovery of unfamiliar code, input formats, specifications, and shared root causes before implementation.",
            "system_prompt": (
                "Inspect the files and rules supplied in the delegation message. Read relevant documentation and docstrings. "
                "Identify shared root causes, data-quality issues, and output requirements. Do not change files. "
                "Return a concise plan with file paths, evidence, and uncertainties; do not invent missing rules."
            ),
        },
        {
            "name": "implementer",
            "description": "Delegate a well-scoped code fix or data/log transformation after supplying every requirement and relevant file path.",
            "system_prompt": (
                "Implement only the delegated work, following all supplied rules and the local documentation. "
                "Fix shared causes rather than symptoms; inspect duplicates, missing values, formats, and time zones when relevant. "
                "Run appropriate tests or validate generated outputs. Report the exact files changed, checks run, and unresolved issues."
            ),
        },
        {
            "name": "reviewer",
            "description": "Delegate an independent check of modified files and generated outputs against specifications before declaring completion.",
            "system_prompt": (
                "Independently inspect the delegated artifacts against every supplied requirement and local specification. "
                "Run tests and check schemas, boundary cases, and output consistency. Do not change files. "
                "Return concrete failures with evidence, or state which checks passed and what remains unverified."
            ),
        },
    ]
