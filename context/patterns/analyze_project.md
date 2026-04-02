# 项目分析

keywords: 性能,优化,分析,审计,依赖,资源

## 分析维度

### 代码
- 搜索性能敏感 API 调用：GetComponent、Find、FindObjectOfType、Camera.main、string +
- 统计各脚本的 Update/FixedUpdate 使用频率

### 资源
- 统计资源文件大小分布，按类型分类
- 标记过大纹理（手游建议 ≤2048x2048，PC ≤4096x4096）
- 标记未压缩的音频文件

### 配置
- 检查 QualitySettings：Shadow Distance 手游建议 ≤50
- 检查 PhysicsManager：碰撞矩阵是否过于宽泛
- 检查质量等级设置
