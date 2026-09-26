import json
import os

from dotenv import load_dotenv

try:  # openai 是可选的：缺失时 generate_summary 走确定性 mock
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

load_dotenv()


class MeetingSummarizer:
    FABRIC_COST_MAP = {
        'cotton': 35,
        'linen': 55,
        'silk': 120,
        'wool': 80,
    }

    COMPLEXITY_MULTIPLIER = {
        'simple': 1.0,
        'medium': 1.5,
        'complex': 2.2,
    }

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if (api_key and OPENAI_AVAILABLE) else None
    
    def generate_summary(self, transcript, design_data, patterns):
        if not self.client:
            return self._mock_summary(transcript, design_data, patterns)
        
        full_transcript = self._format_transcript(transcript)
        
        prompt = f"""
你是一位专业的手工扎染工坊产品开发会议记录员。请根据以下会议内容生成详细的纪要：

会议转录内容：
{full_transcript}

设计数据：
{json.dumps(design_data, ensure_ascii=False, indent=2)}

提取的工艺模式：
{json.dumps(patterns, ensure_ascii=False, indent=2)}

请生成包含以下部分的纪要：
1. 会议主题与系列名称（从讨论中提炼）
2. 关键决策点
3. 图案设计要点（造型、元素、风格）
4. 植物染料配色方案
5. 扎结手法与染色工艺（含次数、温度、时间）
6. 成本核算明细
7. 下一步行动计划
8. 买手店推荐卖点

请用专业但易懂的语言，突出手工扎染的艺术价值和工艺特点。
"""
        
        # 已配置 Key 即真实调用 OpenAI；一旦调用失败（网络错误 / 429 / 鉴权失败），
        # 异常必须向上抛出，绝不允许退回模板摘要伪装成功。
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一位专业的手工艺品开发会议记录员，精通传统扎染工艺和现代设计理念。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return {
            'summary': response.choices[0].message.content,
            'series_theme': self._extract_theme(response.choices[0].message.content),
            'cost_breakdown': self.calculate_cost(design_data)
        }
    
    def _format_transcript(self, transcript):
        lines = []
        for seg in transcript.get('segments', []):
            role = seg.get('role', '参与者')
            speaker = seg.get('speaker', '未知')
            text = seg.get('text', '')
            lines.append(f"[{role} {speaker}] {text}")
        return "\n".join(lines)
    
    def _extract_theme(self, summary_text):
        import re
        theme_match = re.search(r'(系列名称|主题)[：:]\s*(.+?)(?:\n|$)', summary_text)
        if theme_match:
            return theme_match.group(2).strip()
        return "靛蓝手工扎染系列"
    
    def _mock_summary(self, transcript, design_data, patterns):
        text = transcript.get('text', '')
        
        series_theme = design_data.get('series_name', '靛蓝手工扎染系列')
        
        tie_methods = patterns.get('tie_methods', ['扎结', '捆扎'])
        dye_count = patterns.get('dye_count_mentions', 3)
        colors = patterns.get('color_mentions', ['靛蓝', '植物染'])
        
        cost = self.calculate_cost(design_data)
        
        summary = f"""
# 手工扎染工坊产品开发会议纪要

## 1. 会议主题与系列名称
**{series_theme}**

本次会议聚焦于{series_theme}的产品开发，融合传统扎染工艺与现代设计理念，打造独具匠心的手工靛蓝扎染产品系列。

## 2. 关键决策点
- 确定以植物靛蓝为主要染料，突出环保天然的品牌理念
- 采用多种扎结手法结合，创造丰富的纹理层次
- 计划染色次数控制在{dye_count}次左右，实现理想的色彩深度
- 开发{len(tie_methods)}种核心图案，覆盖不同消费场景

## 3. 图案设计要点
- **造型元素**：抽象几何、自然波纹、传统云纹
- **风格定位**：东方美学与现代简约的融合
- **纹理层次**：通过{', '.join(tie_methods)}等手法创造渐变与晕染效果
- **构图原则**：留白与饱满的平衡，体现手工制作的温度感

## 4. 植物染料配色方案
- **主色调**：{', '.join(colors)}
- **辅助色**：浅灰、米白、藏青
- **染色工艺**：多次浸染，自然氧化显色
- **色彩层次**：从浅蓝到深蓝的渐变过渡

## 5. 扎结手法与染色工艺
### 扎结手法：
{chr(10).join([f'- {m}' for m in tie_methods])}

### 染色参数：
- 染色次数：{dye_count}次
- 染缸温度：50-60°C
- 浸染时间：每缸15-20分钟
- 氧化时间：每次染色后静置氧化30分钟
- 媒染工艺：采用天然明矾媒染

## 6. 成本核算明细

**单件产品成本：{cost.get('total_cost', 0)}元**

| 项目 | 成本（元） | 占比 |
|------|-----------|------|
| 面料成本 | {cost.get('fabric_cost', 0)} | {cost.get('fabric_percentage', '0%')} |
| 染料成本 | {cost.get('dye_cost', 0)} | {cost.get('dye_percentage', '0%')} |
| 人工成本 | {cost.get('labor_cost', 0)} | {cost.get('labor_percentage', '0%')} |
| 水电能耗 | {cost.get('utility_cost', 0)} | {cost.get('utility_percentage', '0%')} |
| 其他费用 | {cost.get('other_cost', 0)} | {cost.get('other_percentage', '0%')} |

**建议零售价：{cost.get('suggested_retail', 0)}元**

## 7. 下一步行动计划
1. 完成{len(tie_methods)}款核心图案的打样
2. 进行{dye_count}次染色工艺测试
3. 制作产品系列卡和工艺说明
4. 准备买手店展示样品

## 8. 买手店推荐卖点
- 100%天然植物靛蓝染色，环保健康
- 纯手工扎结，每件作品独一无二
- 传统工艺与现代设计的完美融合
- 可追溯的制作过程，讲述匠人心声
- 限量发售，具有收藏价值
"""
        
        return {
            'summary': summary.strip(),
            'series_theme': series_theme,
            'cost_breakdown': cost,
            'is_mock': True,
        }
    
    def validate_cost_params(self, params):
        """校验成本核算入参，返回规范化后的 (quantity, fabric_type, complexity)。

        非法输入抛出 ValueError，由接口层转成 400。
        """
        params = params or {}
        quantity = params.get('quantity', 1)
        fabric_type = params.get('fabric_type', 'cotton')
        complexity = params.get('complexity', 'medium')

        # bool 是 int 的子类，必须单独排除
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError('quantity 必须是正整数（>= 1）')
        if fabric_type not in self.FABRIC_COST_MAP:
            raise ValueError(
                'fabric_type 必须是以下之一：' + ', '.join(self.FABRIC_COST_MAP)
            )
        if complexity not in self.COMPLEXITY_MULTIPLIER:
            raise ValueError(
                'complexity 必须是以下之一：' + ', '.join(self.COMPLEXITY_MULTIPLIER)
            )

        return quantity, fabric_type, complexity

    def calculate_cost(self, params):
        quantity, fabric_type, complexity = self.validate_cost_params(params)

        base_fabric = self.FABRIC_COST_MAP[fabric_type]
        multiplier = self.COMPLEXITY_MULTIPLIER[complexity]
        
        fabric_cost = base_fabric * quantity
        dye_cost = 15 * quantity * multiplier
        labor_cost = 80 * quantity * multiplier
        utility_cost = 12 * quantity
        other_cost = 8 * quantity
        
        total_cost = fabric_cost + dye_cost + labor_cost + utility_cost + other_cost
        
        suggested_retail = total_cost * 2.8
        
        return {
            'quantity': quantity,
            'fabric_type': fabric_type,
            'complexity': complexity,
            'fabric_cost': round(fabric_cost, 2),
            'dye_cost': round(dye_cost, 2),
            'labor_cost': round(labor_cost, 2),
            'utility_cost': round(utility_cost, 2),
            'other_cost': round(other_cost, 2),
            'total_cost': round(total_cost, 2),
            'suggested_retail': round(suggested_retail, 2),
            'fabric_percentage': f"{round(fabric_cost/total_cost*100, 1)}%",
            'dye_percentage': f"{round(dye_cost/total_cost*100, 1)}%",
            'labor_percentage': f"{round(labor_cost/total_cost*100, 1)}%",
            'utility_percentage': f"{round(utility_cost/total_cost*100, 1)}%",
            'other_percentage': f"{round(other_cost/total_cost*100, 1)}%"
        }
