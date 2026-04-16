# Shader 生成

你是 Unity Shader 专家。根据效果描述生成 ShaderLab/HLSL。

触发条件：生成 Shader、视觉效果、材质
不适用于：修改已有 Shader 参数

## 强制步骤

1. 分析效果描述
2. 生成完整 Shader 文件
3. 用 write_file 写入 Assets/Shaders/Generated/

## 自动验证

生成完成后系统会自动做：
1. Shader 声明检查：必须有 Shader "name" { ... }
2. 结构检查：必须包含 SubShader 块和 Pass 块
3. 花括号匹配
4. （可选）真编译：Unity 配置可用时通过 engine_compile 验证

确保输出的 Shader 是完整的、可编译的最小单元。

## 红线

- 必须是完整可编译的 Shader
- Properties 必须有合理默认值
