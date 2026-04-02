# 代码审查

keywords: 审查,检查,review,代码质量,代码规范

## 审查维度

### 性能
- Update/FixedUpdate 中的 GetComponent/Find/FindObjectOfType → 应在 Awake 缓存
- Camera.main 未缓存 → 每次调用等于 FindWithTag
- 字符串拼接在热路径 → 应使用 StringBuilder
- 频繁 Instantiate/Destroy → 应使用对象池
- LINQ 在 Update 中使用 → 产生 GC

### 规范
- public 字段 → 应改为 [SerializeField] private
- gameObject.tag == "xxx" → 应使用 CompareTag()
- 命名不规范（字段 _camelCase，方法 PascalCase，常量 UPPER_CASE）
- 魔法数字 → 应提取为常量或 [SerializeField]
- 方法超过 30 行 → 应拆分

### 反模式
- SendMessage/BroadcastMessage → 应使用事件或接口
- 未退订的事件监听 → OnDestroy 中退订
- 在协程中使用 new WaitForSeconds → 应缓存

### 安全
- 未检查 null（GetComponent 可能返回 null）
- 数组/列表越界风险
- 除零风险
