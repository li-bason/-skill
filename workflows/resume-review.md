# 恢复与更新流程

1. 从 `sessions/` 或用户给出的任务名定位唯一任务目录。
2. 依次读取 `progress-log.md`、`review_lock.yaml`、`source_manifest.json`、
   `review_spec.md`；只按需读取正式产物。
3. 新材料先通过 `scripts/import_sources.py` 登记，不直接覆盖旧 manifest。
4. 比较新增来源与现有覆盖，写入 `update_plan.json`：
   - 新章节/专题：更新对应知识点、思维导图、题目和答案。
   - 题型变化：整体重排题目与答案。
   - 大纲变化：重新计算范围与覆盖矩阵。
   - 仅文字修订：局部更新，不重生成无关题目。
5. 若任务目标、类别或输出结构发生实质变化，先更新 `review_spec.md` 并请求一次确认；
   普通增量更新无需重复确认。
6. 更新受影响产物，保持既有稳定 ID；删除内容时在变更计划记录原因。
7. 重跑合同、内容、覆盖矩阵和 session 校验。

同一任务只维护一个 session 文件，不按日期创建多个会话目录。每阶段都覆盖更新
`progress-log.md`，其中保留最近变更摘要和下一步。
