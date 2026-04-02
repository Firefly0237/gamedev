# 修改代码

keywords: 改代码,修改方法,改变量,改参数,重构

## 执行步骤

1. 确定目标代码文件
2. 找到要修改的精确原始文本（search_pattern）
3. 编写替换后的文本（replace_with）
4. search_pattern 必须在文件中唯一匹配
5. 输出 CodeModifyPlan JSON

## 约束

- search_pattern 必须精确匹配文件中的原始内容
- 如果匹配到多处，拒绝执行并要求用户提供更精确的定位
- 不修改无关代码
