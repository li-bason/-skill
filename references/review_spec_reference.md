# Review Spec Reference

`review_spec.md` 是用户可读的任务设计书，在正式生成前由用户确认。至少包含：

## Task Information

- 任务名称、类型和分类。禁止询问考试/比赛日期与可用复习时间；用户主动提供时可记录，
  未提供时省略，不写“待提供”，也不得追加相关问题。

## Scope & Inputs

- 复习边界、材料清单、材料优先级、缺失输入和冲突。

## Template Selection

- 从 `templates/index.json` 选择的三个模板 ID、版本、路径与理由。

## Output Plan

- 正式产物文件、每份文件的作用、深度和预计规模。

## Content Strategy

- 章节/专题切分、最细知识点定义、思维导图组织和压缩原则。

## Question Strategy

- 题型、题目来源、每点最低题量、基础 40% / 中等 40% / 综合 20% 的难度策略。

## Source & External Supplement Policy

- 来源状态、外部补充条件、引用方式、未验证内容和冲突处理。

## Delivery & Update Policy

- 任务目录、session、增量更新、去重重整、校验和交付格式。

用户确认后，将机器约束写入 `review_lock.yaml`。如果两者冲突，以已确认的
`review_lock.yaml` 为准，但不得静默改变用户目标。
