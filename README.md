# 踏线 · 马术学校课前场地停用预估

牧岸马术学校有 3 块围场、2 名场务和 6 名教员。雨天巡场纸单常与当天课表脱节，难判断什么样的湿度曾停过课、目标场能否容纳整班、以及哪条观察触发移场。系统把巡场、停用意见和有容量约束的课表分开保存，下游由教务确认通知。

## 一天的工作顺序

1. 07:55 核对 OUT、COV、LOW 围场容量。
2. 08:00 巡场 CSV 登记 W20，积水 45%。
3. 08:15 对 OUT 计算一层分类树；看停用概率和两条保留样本。
4. 08:25 为 4 人的 L09 尝试 LOW，容量 3 人被拦。
5. 08:30 复核 COV 同日清场记录 W22。
6. 08:35 复核员把初级 6 班移入 COV，保存关联 W20。
7. 08:45 教务在课时页抄送更新结果。

## 算法口径

按日期留末两条巡场事实作独立验证，前八条拟合一层分类树。枚举三个字段的相邻中点，以两个节点加权基尼最小的切分为准，叶子频率给出停用概率。按漏停成本为误停三倍，阈值取 0.25。封栏记录直接建议停用。

## 上手

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
docker compose down --remove-orphans
```

前端走本机 **18458**，API 走 **19458**，PostgreSQL 走 **17958**。本地开发可在安装 Python 3.11、PostgreSQL 和 Redis 后配置与 Compose 相同的环境变量，在 backend 运行 `uvicorn app:app --reload`，前端以 Nginx 同源代理启动。

| 角色 | 邮箱 | 业务权限 |
|---|---|---|
| 录入员 | operator@demo.local | 登记巡场、计算概率 |
| 复核员 | reviewer@demo.local | 确认同日可用记录和容量，签核移场 |
| 查阅员 | viewer@demo.local | 查场牌和课表 |

三个演示账号默认密码均为 `Demo2026!`。使用本地合成样本，seed 只插入缺失的自然键。关闭 `SEED_DEMO` 可跳过自动 seed。使用自己的 `JWT_SECRET`、`POSTGRES_PASSWORD` 和 `DEMO_PASSWORD` 部署。

| 目录 | 技术与职责 |
|---|---|
| backend | Python 3.11 / FastAPI，使用 PostgreSQL 16；Worker 轮询持久化队列，Redis 为登录限流及健康检查提供支持 |
| frontend | Nginx、HTML、CSS、JavaScript ES modules，HTTP 同源代理 |
| docker-compose.yml | 5 服务及健康检查、独立卷；Redis 与 worker 无宿主端口 |

角色、作业状态在 `backend/core.py`、`frontend/base.js` 定义，在 `backend/core.py`（鉴权、队列）与 `backend/worker.py` 使用。领域阶段由数据库约束与业务服务维护，`frontend/view.js` 负责显示。接口输出为最新已提交状态。

用于演示的单层树只基于十条历史记录，最终处置由场务和教务人工复核。

MIT License
