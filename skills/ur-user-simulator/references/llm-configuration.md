# 外部模型配置

复制项目根目录的 [`config/llm.example.yaml`](../../../config/llm.example.yaml)，只填写要使用的模型 ID。行尾注释是该提供商对应的 Key 环境变量；在环境变量中设置 Key，不要写入 YAML。

提供商 ID、默认基础地址、接口类型和请求差异已内置于 `run_simulation.py`。空模型或缺少 Key 的提供商自动跳过；没有可用自定义模型时，脚本返回 `fallback_current_model`，主 Skill 改用当前模型。

其他地域或专属工作区不使用这份简洁 YAML；由用户提供对应接口信息后再单独适配，不猜测地址。
