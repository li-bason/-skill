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

所有 review frame、subject preset 和 question pattern 共同遵守“考查要求＋分块内容”契约。
分块名称随学科变化，但不得省略考查要求，也不得把定义、论据、公式、步骤、例题和结论
堆在同一段或同一个表格单元格中。

文科、理科、工科使用同一个 `final-three-files.md` 通用骨架，只通过 subject preset 扩展内容块：

- 文科：概念、背景、原因、内容、影响、论据、评价、结论。
- 理科：定义、定理、公式、推导、例题、结论；长推导逐步换行。
- 工科：概念、原理、参数、流程、伪代码、应用、注意事项、结论。

目录过滤、去重、来源隔离、同考点出题、乱码拦截、PDF目检和临时目录清理是三类共同规则，
不得在某个 preset 中关闭。

逐点排版同样是共同规则：并列内容一项一行，顺序内容一步一行。它适用于文科论据与影响、
理科推导与证明、工科流程与注意事项，也适用于语言策略和竞赛解法。
