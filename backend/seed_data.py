"""
种子数据脚本
建表 + 插入来源/标签/样题（含 LaTeX 题干、选项、解析、标签）
运行: cd backend && python seed_data.py
"""
import asyncio
import sys

from app.database import engine, Base, async_session
from app.models import Source, Question, Option, Solution, Tag, question_tags

# 确保所有模型注册
import app.models  # noqa: F401


async def reset_db():
    """删除并重建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[✓] 数据库表已重建")


async def seed():
    """插入种子数据"""
    async with async_session() as db:
        # ---------- 来源 ----------
        sources = [
            Source(book_title="Heard on the Street: Quantitative Questions from Wall Street Job Interviews",
                   author="Timothy Falcon Crack", edition="3rd", notes="华尔街经典面试题集"),
            Source(book_title="QuantitativePrimer", author="Unknown", notes="入门级量化练习"),
            Source(book_title="A Practical Guide to Quantitative Finance Interviews",
                   author="Xinfeng Zhou", edition="2008", notes="俗称绿皮书"),
        ]
        db.add_all(sources)
        await db.flush()  # 获取 id
        s_hot, s_primer, s_green = sources

        # ---------- 标签 ----------
        tag_defs = [
            # 知识点
            ("概率论", "knowledge"), ("条件概率", "knowledge"), ("期望", "knowledge"),
            ("随机过程", "knowledge"), ("布朗运动", "knowledge"), ("期权定价", "knowledge"),
            ("统计", "knowledge"), ("蒙特卡洛", "knowledge"), ("brain teaser", "knowledge"),
            ("线性代数", "knowledge"), ("微积分", "knowledge"),
            # 岗位
            ("量化研究", "position"), ("量化交易", "position"), ("量化开发", "position"),
        ]
        tags = [Tag(name=n, type=t) for n, t in tag_defs]
        db.add_all(tags)
        await db.flush()
        # 建立名称→标签映射
        tag_map = {t.name: t for t in tags}

        # ---------- 题目 ----------
        questions_data = [
            # --- Q1: 概率选择题 ---
            {
                "stem": "两枚公平骰子同时掷出，求两枚骰子点数之和为 7 的概率。\n\n$$P(\\text{sum}=7) = ?$$",
                "type": "choice", "difficulty": 1, "chapter": "Probability Basics",
                "source": s_hot, "page": 12,
                "options": [
                    ("A", "$\\frac{1}{9}$", False),
                    ("B", "$\\frac{1}{6}$", True),
                    ("C", "$\\frac{5}{36}$", False),
                    ("D", "$\\frac{7}{36}$", False),
                ],
                "solution": "点数和为 7 的组合有 (1,6),(2,5),(3,4),(4,3),(5,2),(6,1) 共 6 种，总组合数 36。\n\n$$P(\\text{sum}=7) = \\frac{6}{36} = \\frac{1}{6}$$",
                "tags": ["概率论", "量化研究"],
            },
            # --- Q2: 条件概率 ---
            {
                "stem": "某疾病患病率为 1/1000，检测准确率 99%（即患病者 99% 阳性，健康者 99% 阴性）。某人检测阳性，实际患病的概率是多少？",
                "type": "choice", "difficulty": 3, "chapter": "Conditional Probability",
                "source": s_green, "page": 45,
                "options": [
                    ("A", "$99\\%$", False),
                    ("B", "$\\approx 9\\%$", True),
                    ("C", "$\\approx 1\\%$", False),
                    ("D", "$\\approx 50\\%$", False),
                ],
                "solution": "贝叶斯定理：\n\n$$P(D|+) = \\frac{P(+|D)P(D)}{P(+|D)P(D)+P(+|\\neg D)P(\\neg D)}$$\n\n$$= \\frac{0.99 \\times 0.001}{0.99 \\times 0.001 + 0.01 \\times 0.999} \\approx 0.09$$\n\n即约 9%。这是经典的基础率忽视问题。",
                "tags": ["条件概率", "概率论", "量化研究"],
            },
            # --- Q3: 期望填空 ---
            {
                "stem": "设 $X \\sim N(0, 1)$，求 $E[X^4] =$ ?",
                "type": "fill", "difficulty": 2, "chapter": "Expectation",
                "source": s_primer, "page": 23,
                "options": [],
                "solution": "标准正态分布的偶数阶矩：$E[X^{2n}] = (2n-1)!!$\n\n$$E[X^4] = 3!! = 3 \\times 1 = 3$$",
                "tags": ["期望", "概率论", "量化研究"],
            },
            # --- Q4: brain teaser ---
            {
                "stem": "你有 25 匹马，想选出跑得最快的 3 匹。赛马场每次最多 5 匹马同时比赛，且只能看到名次不能计时。最少需要赛多少场才能确定前三名？",
                "type": "choice", "difficulty": 3, "chapter": "Brain Teasers",
                "source": s_hot, "page": 5,
                "options": [
                    ("A", "5 场", False),
                    ("B", "6 场", False),
                    ("C", "7 场", True),
                    ("D", "8 场", False),
                ],
                "solution": "**答案：7 场**\n\n1. 先分 5 组各赛 1 场（共 5 场），得每组内部排名。\n2. 第 6 场：5 个组冠军赛，确定总排名第一，且淘汰部分组。\n3. 第 7 场：取可能与第 2、3 名有关的马（第 6 场的第 2、3 名所在组的第 2、3 名，第 6 场冠军组的第 2、3 名，第 6 场第 2 名组的第 2 名），共 5 匹再赛 1 场，取前 2 名即为总第 2、3 名。",
                "tags": ["brain teaser", "量化交易"],
            },
            # --- Q5: 期权定价简答 ---
            {
                "stem": "简述 Black-Scholes 期权定价模型的 5 个核心假设，并写出欧式看涨期权的定价公式。",
                "type": "short", "difficulty": 4, "chapter": "Option Pricing",
                "source": s_green, "page": 120,
                "options": [],
                "solution": "**5 个核心假设：**\n1. 股票价格服从几何布朗运动 $dS = \\mu S\\,dt + \\sigma S\\,dW$\n2. 无风险利率 $r$ 恒定\n3. 波动率 $\\sigma$ 恒定\n4. 无交易成本和税收\n5. 允许连续卖空且可全天交易\n\n**欧式看涨期权定价公式：**\n\n$$C = S_0 N(d_1) - Ke^{-rT}N(d_2)$$\n\n其中 $d_1 = \\frac{\\ln(S_0/K)+(r+\\sigma^2/2)T}{\\sigma\\sqrt{T}}$，$d_2 = d_1 - \\sigma\\sqrt{T}$，$N(\\cdot)$ 为标准正态分布累积函数。",
                "tags": ["期权定价", "随机过程", "量化研究"],
            },
            # --- Q6: 布朗运动证明 ---
            {
                "stem": "证明：标准布朗运动 $W_t$ 的二次变分为 $\\langle W \\rangle_t = t$。",
                "type": "proof", "difficulty": 5, "chapter": "Stochastic Calculus",
                "source": s_green, "page": 200,
                "options": [],
                "solution": "**证明：**\n\n对 $[0,t]$ 的分割 $\\pi_n: 0=t_0<t_1<\\cdots<t_n=t$，令 $|\\pi_n|=\\max|t_i-t_{i-1}|$。\n\n二次变分定义为：$\\langle W \\rangle_t = \\lim_{|\\pi_n|\\to 0} \\sum_{i=1}^n (W_{t_i}-W_{t_{i-1}})^2$\n\n由 $W_{t_i}-W_{t_{i-1}} \\sim N(0, \\Delta t_i)$，故 $E[(\\Delta W_i)^2]=\\Delta t_i$，$\\text{Var}[(\\Delta W_i)^2]=2(\\Delta t_i)^2$。\n\n$$\\sum (\\Delta W_i)^2 \\to t \\quad (L^2)$$\n\n因为 $E[\\sum(\\Delta W_i)^2]=\\sum \\Delta t_i = t$，且方差 $\\sum 2(\\Delta t_i)^2 \\to 0$。证毕。",
                "tags": ["随机过程", "布朗运动", "量化研究"],
            },
            # --- Q7: 蒙特卡洛 ---
            {
                "stem": "用蒙特卡洛方法估计 $\\pi$ 的值。给出基本思路和收敛速度。",
                "type": "short", "difficulty": 2, "chapter": "Monte Carlo Methods",
                "source": s_primer, "page": 50,
                "options": [],
                "solution": "**基本思路：** 在 $[-1,1]\\times[-1,1]$ 正方形内随机投点 $N$ 次，统计落入单位圆内的点数 $M$。\n\n$$\\frac{\\pi \\cdot 1^2}{4} \\approx \\frac{M}{N} \\implies \\pi \\approx \\frac{4M}{N}$$\n\n**收敛速度：** 蒙特卡洛误差 $\\sim O(1/\\sqrt{N})$，即精度每提高 1 位需 100 倍样本。",
                "tags": ["蒙特卡洛", "概率论", "量化开发"],
            },
            # --- Q8: 线性代数 ---
            {
                "stem": "设 $A$ 为 $n \\times n$ 实对称矩阵，证明其特征值均为实数。",
                "type": "proof", "difficulty": 4, "chapter": "Linear Algebra",
                "source": s_green, "page": 80,
                "options": [],
                "solution": "**证明：**\n\n设 $\\lambda$ 为 $A$ 的特征值，$v$ 为对应特征向量（复向量），$Av=\\lambda v$。\n\n取共轭转置：$v^* A^* = \\bar{\\lambda} v^*$。因 $A$ 实对称，$A^*=A$，故 $v^* A = \\bar{\\lambda} v^*$。\n\n左乘 $v^*$ 于 $Av=\\lambda v$：$v^*Av = \\lambda v^*v$。\n\n又 $v^*Av = \\bar{\\lambda} v^*v$。\n\n故 $(\\lambda - \\bar{\\lambda})v^*v = 0$。因 $v^*v > 0$，故 $\\lambda = \\bar{\\lambda}$，即 $\\lambda$ 为实数。证毕。",
                "tags": ["线性代数", "量化研究"],
            },
            # --- Q9: 统计 ---
            {
                "stem": "什么是大数定律？写出弱大数定律的形式并简述其含义。",
                "type": "short", "difficulty": 1, "chapter": "Statistics",
                "source": s_hot, "page": 30,
                "options": [],
                "solution": "**弱大数定律（WLLN）：**\n\n设 $X_1, X_2, \\ldots$ 独立同分布，$E[X_i]=\\mu$，则样本均值依概率收敛于期望：\n\n$$\\bar{X}_n = \\frac{1}{n}\\sum_{i=1}^n X_i \\xrightarrow{P} \\mu \\quad (n \\to \\infty)$$\n\n**含义：** 样本量足够大时，样本均值会以很高概率接近真实期望。这是蒙特卡洛方法的理论基础。",
                "tags": ["统计", "概率论", "量化研究"],
            },
            # --- Q10: 期望计算 ---
            {
                "stem": "设 $X$ 和 $Y$ 独立，$X \\sim \\text{Poisson}(\\lambda_1)$，$Y \\sim \\text{Poisson}(\\lambda_2)$，求 $E[X | X+Y=n]$。",
                "type": "choice", "difficulty": 4, "chapter": "Conditional Expectation",
                "source": s_green, "page": 95,
                "options": [
                    ("A", "$\\frac{n}{\\lambda_1+\\lambda_2}$", False),
                    ("B", "$\\frac{n\\lambda_1}{\\lambda_1+\\lambda_2}$", True),
                    ("C", "$\\frac{n\\lambda_2}{\\lambda_1+\\lambda_2}$", False),
                    ("D", "$\\lambda_1$", False),
                ],
                "solution": "已知 $X+Y \\sim \\text{Poisson}(\\lambda_1+\\lambda_2)$，且在 $X+Y=n$ 条件下 $X \\sim \\text{Binomial}(n, \\frac{\\lambda_1}{\\lambda_1+\\lambda_2})$。\n\n$$E[X|X+Y=n] = n \\cdot \\frac{\\lambda_1}{\\lambda_1+\\lambda_2}$$",
                "tags": ["条件概率", "期望", "概率论", "量化研究"],
            },
            # --- Q11: 微积分 ---
            {
                "stem": "计算积分 $\\int_0^{\\infty} e^{-x^2} dx$。",
                "type": "fill", "difficulty": 3, "chapter": "Calculus",
                "source": s_primer, "page": 15,
                "options": [],
                "solution": "高斯积分：\n\n$$\\int_0^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$\n\n可用极坐标变换证明：$\\left(\\int_{-\\infty}^{\\infty} e^{-x^2}dx\\right)^2 = \\int\\int e^{-(x^2+y^2)}dxdy = \\pi$，故 $\\int_{-\\infty}^{\\infty} = \\sqrt{\\pi}$。",
                "tags": ["微积分", "概率论", "量化研究"],
            },
            # --- Q12: 随机过程 ---
            {
                "stem": "什么是鞅（martingale）？给出定义并举一个例子。",
                "type": "short", "difficulty": 3, "chapter": "Stochastic Processes",
                "source": s_green, "page": 180,
                "options": [],
                "solution": "**定义：** 随机过程 $\\{M_t, \\mathcal{F}_t\\}$ 是鞅，若：\n1. $E[|M_t|] < \\infty$\n2. $E[M_t | \\mathcal{F}_s] = M_s$（$\\forall s < t$）\n\n**含义：** 在已知信息 $\\mathcal{F}_s$ 下，未来时刻的最佳预测就是当前值。\n\n**例子：** 标准布朗运动 $W_t$ 是鞅，因为 $E[W_t | \\mathcal{F}_s] = E[W_t - W_s + W_s | \\mathcal{F}_s] = W_s$。",
                "tags": ["随机过程", "量化研究"],
            },
            # --- Q13: 编程向 ---
            {
                "stem": "在量化开发中，什么是事件驱动回测（event-driven backtesting）？它与向量化回测的区别是什么？",
                "type": "short", "difficulty": 3, "chapter": "Quantitative Development",
                "source": s_primer, "page": 70,
                "options": [],
                "solution": "**事件驱动回测：** 模拟真实交易环境，通过事件队列（MarketEvent/SignalEvent/OrderEvent/FillEvent）驱动策略执行，逐 bar 处理。\n\n**与向量化回测的区别：**\n| 维度 | 向量化 | 事件驱动 |\n|------|--------|---------|\n| 速度 | 快（矩阵运算） | 慢（逐事件循环） |\n| 真实性 | 低（忽略执行细节） | 高（模拟滑点、延迟、手续费） |\n| 适用 | 快速策略筛选 | 最终验证 |\n\n量化开发岗常见考点。",
                "tags": ["量化开发"],
            },
            # --- Q14: 概率 ---
            {
                "stem": "三人独立地向同一目标射击，命中率分别为 0.5、0.6、0.8。目标被击中的概率是多少？",
                "type": "choice", "difficulty": 1, "chapter": "Probability Basics",
                "source": s_hot, "page": 10,
                "options": [
                    ("A", "$0.96$", True),
                    ("B", "$0.94$", False),
                    ("C", "$0.90$", False),
                    ("D", "$0.84$", False),
                ],
                "solution": "用对立事件：三人都没命中的概率 $= (1-0.5)(1-0.6)(1-0.8) = 0.5 \\times 0.4 \\times 0.2 = 0.04$。\n\n$$P(\\text{击中}) = 1 - 0.04 = 0.96$$",
                "tags": ["概率论", "量化研究"],
            },
            # --- Q15: 蒙特卡洛方差减少 ---
            {
                "stem": "什么是蒙特卡洛方法中的对偶变量法（antithetic variates）？如何用它减少方差？",
                "type": "short", "difficulty": 4, "chapter": "Monte Carlo Methods",
                "source": s_green, "page": 150,
                "options": [],
                "solution": "**对偶变量法：** 对每个随机样本 $U \\sim \\text{Uniform}(0,1)$，同时使用 $U$ 和 $1-U$ 生成一对样本，取两者估计的均值。\n\n**原理：** 若估计量关于输入单调，则 $f(U)$ 与 $f(1-U)$ 负相关，使 $\\text{Var}\\left[\\frac{f(U)+f(1-U)}{2}\\right]$ 小于 $\\text{Var}[f(U)]/2$。\n\n**效果：** 在不增加样本数的前提下减少方差，提升蒙特卡洛收敛速度。常用于期权定价。",
                "tags": ["蒙特卡洛", "概率论", "量化研究"],
            },
        ]

        # 创建题目
        for i, qd in enumerate(questions_data):
            q = Question(
                stem_markdown=qd["stem"],
                question_type=qd["type"],
                difficulty=qd["difficulty"],
                source_id=qd["source"].id,
                book_page=qd.get("page"),
                book_chapter=qd.get("chapter"),
                status="published",
            )
            db.add(q)
            await db.flush()

            # 选项
            for label, content, is_correct in qd["options"]:
                db.add(Option(
                    question_id=q.id, label=label,
                    content_markdown=content, is_correct=is_correct,
                ))

            # 解析
            db.add(Solution(
                question_id=q.id, content_markdown=qd["solution"],
                source_id=qd["source"].id, version=1,
            ))

            # 标签关联
            for tname in qd["tags"]:
                if tname in tag_map:
                    await db.execute(
                        question_tags.insert().values(
                            question_id=q.id, tag_id=tag_map[tname].id
                        )
                    )

            await db.flush()
            print(f"  [✓] Q{q.id}: {qd['type']} | {qd['chapter']} | 难度{qd['difficulty']}")

        await db.commit()

    print(f"\n[✓] 种子数据插入完成，共 {len(questions_data)} 道题")


async def main():
    print("=" * 50)
    print("量化面试刷题题库平台 - 种子数据初始化")
    print("=" * 50)
    await reset_db()
    await seed()
    print("\n完成！启动服务: uvicorn app.main:app --reload --port 8000")
    print("API 文档: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
