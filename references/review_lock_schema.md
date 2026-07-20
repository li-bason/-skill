# Review Lock Schema

`review_lock.yaml` 使用 JSON 语法保存；JSON 是合法 YAML，且可由 Python 标准库稳定解析。

必填结构：

```json
{
  "version": 1,
  "task": {
    "mode": "final_exam|contest",
    "name": "任务名",
    "category": "liberal-arts|science|engineering|language|contest-general",
    "task_dir": "tasks/期末/名称"
  },
  "templates": {
    "review_frame": "索引中的模板 ID",
    "subject_preset": "索引中的模板 ID",
    "question_pattern": "索引中的模板 ID"
  },
  "inputs": {
    "manifest": "source_manifest.json",
    "outline_required": true,
    "question_types_required": true
  },
  "outputs": ["知识点.md", "思维导图.md", "题目.md", "答案.md"],
  "rules": {
    "minimum_questions_per_point": 3,
    "difficulty_ratio": {"basic": 0.4, "medium": 0.4, "advanced": 0.2},
    "stable_ids": true,
    "source_attribution": true,
    "update_mode": "incremental_with_reorganize"
  }
}
```

合同一经确认，后续不得静默改变输出列表、模板、最低题量或任务分类。

语言积累任务使用三个输出：`词汇语法积累表.md`、`翻译积累表.md`、`写作积累表.md`；规则中
设置 `minimum_questions_per_point: 0`、`accumulation_only: true`，且模板选择
`language-accumulation-v1`。语言任务不声明题目、答案、阅读或思维导图产物。
