"""评分Rubric数据结构 — 定义LLM-as-Judge的评分维度和评分标准"""

from dataclasses import dataclass, field


@dataclass
class RubricDimension:
    """单个评分维度

    Usage:
        clarity = RubricDimension(
            name="clarity",
            description="提示词是否清晰定义了工作步骤",
            scale={
                1: "完全模糊，无法理解要做什么",
                2: "部分清晰，但步骤不完整或混乱",
                3: "基本清晰，步骤可理解但可以更精确",
                4: "清晰，步骤明确且有逻辑",
                5: "非常清晰，每一步都有可操作的具体描述",
            },
            weight=1.0,
        )
    """

    name: str
    description: str
    scale: dict[int, str]
    weight: float = 1.0

    def __post_init__(self):
        if not self.scale:
            raise ValueError(f"Dimension '{self.name}' must have a non-empty scale dict")
        if not (1 <= min(self.scale.keys()) <= 5 and 1 <= max(self.scale.keys()) <= 5):
            raise ValueError(f"Dimension '{self.name}' scale must be 1-5")


@dataclass
class EvalRubric:
    """完整评分Rubric — 用于LLM-as-Judge评估

    Usage:
        rubric = EvalRubric(
            name="prompt-quality",
            description="评估Worker系统提示词的质量",
            dimensions=[clarity, completeness, actionability],
        )
        prompt = rubric.to_scoring_prompt(subject="Searcher system prompt", output=system_prompt)
    """

    name: str
    description: str
    dimensions: list[RubricDimension]
    reference_answer: str | None = None
    pairwise_only: bool = False
    bias_mitigation: dict = field(default_factory=lambda: {
        "position": True,
        "verbosity": True,
        "self_enhancement": True,
    })

    def to_scoring_prompt(self, subject: str, output: str) -> str:
        """生成LLM评分提示词（绝对评分模式）

        包含完整的评分维度和1-5分标准，要求LLM输出结构化JSON。
        """
        dims_text = "\n".join(
            f"### {i+1}. {d.name}: {d.description}\n"
            + "\n".join(f"  - {score}分: {desc}" for score, desc in sorted(d.scale.items()))
            for i, d in enumerate(self.dimensions)
        )

        weights_text = ", ".join(f'"{d.name}"' for d in self.dimensions)
        ref_section = ""
        if self.reference_answer:
            ref_section = f"\n## 参考答案\n{self.reference_answer}"

        prompt = f"""## 评估Rubric: {self.name}

### 描述
{self.description}

### 评估主题
{subject}

### 被评估的输出
```
{output[:2000]}
```
{ref_section}

### 评分维度与标准
{dims_text}

### 评分规则
1. 对每个维度给出1-5的整数分数（不允许0分或小数）
2. 总分 = 各维度分数加权平均（权重均为1.0）
3. 提供详细的评分理由（至少50字）
4. 给出你对本次评分的置信度（0-1）

### 输出格式
请严格按以下JSON格式输出，不要添加任何其他文本：
```json
{{
  "dimension_scores": {{{weights_text}}},
  "overall_score": 0.0,
  "reasoning": "评分理由...",
  "confidence": 0.0
}}
```

重要提醒：
- 你正在评估另一个系统的输出，请保持客观和批判性
- 不要因为输出看起来"AI生成的"就给高分
- 严格按照评分标准给分，不要宽容或严厉
"""
        return prompt

    def to_comparison_prompt(self, subject: str, output_a: str, output_b: str) -> str:
        """生成成对比较提示词（用于A/B对比评估）

        让LLM同时看到A和B两份输出，判断哪个更好。
        """
        dim_names = ", ".join(d.name for d in self.dimensions)

        prompt = f"""## 成对比较: {self.name}

### 描述
{self.description}

### 评估主题
{subject}

### 评估维度
{dim_names}

### 输出 A
```
{output_a[:1500]}
```

### 输出 B
```
{output_b[:1500]}
```

### 比较规则
1. 从{len(self.dimensions)}个维度分别比较A和B
2. 对每个维度给出A更好/B更好/平局 的判断
3. 给出1-5的整体偏好分数（A分数和B分数）
4. 总分=5表示一方显著优于另一方

### 输出格式
```json
{{
  "winner": "A",  // "A" 或 "B" 或 "tie"
  "score_a": 3.0,
  "score_b": 2.0,
  "reasoning": "比较理由..."
}}
```

重要提醒：
- 比较时不要受文本长度影响（长不等于好）
- 比较时不要受输出顺序影响（A排前面不等于A更好）
"""
        return prompt

    def get_dimension_names(self) -> list[str]:
        return [d.name for d in self.dimensions]
