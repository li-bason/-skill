# 模板选择

先读取 `templates/index.json`，只选择索引中存在的模板文件。

## 期末

| 分类 | review frame | subject preset | question pattern |
|---|---|---|---|
| liberal-arts | `final-three-files.md` | `liberal-arts.md` | `liberal-arts-answer.md` |
| science | `final-three-files.md` | `science.md` | `calculation-answer.md` |
| engineering | `final-three-files.md` | `engineering.md` | `calculation-answer.md` |
| language | `language-summary.md` | `language.md` | `language-practice.md` |

## 竞赛

使用 `contest-gap-training.md`、`contest-general.md` 和
`contest-gap-question.md`。

把所选模板的 ID、版本和相对路径写入 `review_spec.md` 与 `review_lock.yaml`。恢复任务
时复用现有选择，除非用户目标或分类发生实质变化。
