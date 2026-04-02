# 实现游戏系统

keywords: 系统,实现,做一个,加一个,新功能,新机制,模块

## 执行步骤

1. 分析需求，确定需要哪些数据结构
2. 生成数据类（使用项目已有的命名空间和编码风格）
3. 生成初始配置 JSON（如果系统需要可配置数据）
4. 生成核心逻辑脚本（引用步骤 2 的数据类）
5. 生成 NUnit 测试
6. 所有文件遵循项目的目录结构和命名规范

## 文件位置

- 数据类: Assets/Scripts/Data/{Name}Data.cs
- 配置: Assets/Resources/Configs/{Name}Config.json
- 逻辑: Assets/Scripts/Systems/{Name}System.cs
- 测试: Assets/Tests/Editor/{Name}SystemTests.cs

## 约束

- System 脚本默认不继承 MonoBehaviour（纯逻辑类），除非需要 Update 或协程
- 配置加载使用项目已有的模式（参考项目数据格式中已有的配置文件）
- 所有公共方法加 XML 文档注释
- 数据类标记 [System.Serializable]
