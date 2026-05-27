# Agent Plugin Contract — 插件契约规范 v1.0

> 成熟度: 🟢 稳定 — 5 个 Worker 均基于此协议实现，协议自 v1.0 未变更。


## 1. 通用契约 (PluginBase)

所有插件必须继承 `backend.agent.plugin_base.PluginBase` 并实现:

```python
class MyPlugin(PluginBase):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="my-plugin",
            version="1.0.0",
            capabilities=["my-capability"],
        )

    async def on_load(self, config: dict) -> None:
        # 初始化资源
        ...

    async def on_unload(self) -> None:
        # 清理资源
        ...

    async def health_check(self) -> bool:
        return True

    async def on_error(self, error: Exception) -> RecoveryAction:
        return RecoveryAction.RETRY
```

## 2. LLM Adapter Contract

接口: `backend.agent.plugins.llm_adapter.base.LLMAdapterBase`
能力: `llm`

必须实现:
- `chat(messages, temperature, max_tokens) -> LLMResponse`
- `chat_stream(messages, temperature, max_tokens) -> AsyncGenerator[str, None]`
- `evaluate_urgency(tasks, context) -> list[UrgencyAssessment]`

已实现:
- `DeepSeekV4Adapter` (主力)
- `QwenAdapter` (备选)

添加新模型:
```python
class MyLLM(LLMAdapterBase):
    # 实现上述 3 个方法
    ...

# 注册
LLMFactory.register("my-llm", MyLLM)
```

## 3. TTS Engine Contract

接口: `backend.agent.plugins.tts_engine.base.TTSEngineBase`
能力: `tts`

必须实现:
- `synthesize(text, voice, speed) -> TTSResult`
- `available_voices() -> list[str]`

已实现:
- `QwenTTSEngine` (主力, Qwen3-TTS)
- `EdgeTTSEngine` (备份, Microsoft Edge TTS)

## 4. Priority Engine Contract

接口: `backend.agent.plugins.priority_engine.base.PriorityEngineBase`
能力: `priority`

必须实现:
- `evaluate(tasks, context) -> list[ScoredTask]`
- `needs_alert(scored_task) -> bool`

已实现:
- `WeightedScorer` (加权评分 + LLM 辅助)

## 5. Notifier Contract

接口: `backend.agent.plugins.notifier.base.NotifierBase`
能力: `notify`

必须实现:
- `notify(alert: Alert) -> bool`

已实现:
- `VoiceAlert` (TTS 语音提醒)
- `DesktopToast` (Windows Toast)

## 6. Event Bus Events

| Event Type | Data | When |
|-----------|------|------|
| `priority.changed` | `{task_id, old_score, new_score}` | 任务优先级变化 |
| `task.deadline_near` | `{task_id, content, hours_left}` | 任务临近截止 |
| `schedule.tick` | `{timestamp}` | 定时评估触发 |
| `voice.alert_triggered` | `{task_id, message}` | 语音提醒触发 |
| `plugin.loaded` | `{capability, name}` | 插件加载完成 |
| `plugin.unloaded` | `{capability, name}` | 插件卸载 |
| `agent.error` | `{source, error, action}` | 智能体异常 |

## 7. 配置 (agent-config.yaml)

```yaml
agent:
  cron: "*/20 * * * *"  # 评估频率

plugins:
  llm:
    default: "deepseek"  # 默认 LLM
  tts:
    default: "qwen"      # 默认 TTS
    fallback: "edge"     # TTS 降级
  priority:
    algorithm_weight: 0.6  # 算法权重
    llm_weight: 0.4        # LLM 权重
  notify:
    default: "voice"
    fallback: "toast"
```

## 8. 环境变量

- `DEEPSEEK_API_KEY` — DeepSeek API 密钥 (必填)
- `DEEPSEEK_API_BASE` — DeepSeek API 地址 (可选, 默认官方)
- `QWEN_API_KEY` — 阿里云 API 密钥 (TTS 必填)
