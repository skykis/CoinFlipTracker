# CoinFlipTracker

游戏王 Master Duel 硬币/先后手/决斗胜负统计工具（手动录入，长期记录当天与累计）。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 录入

- 点击三组按钮：硬币（赢/输）、先后手（先手/后手）、决斗（胜/负），按 Enter 或"保存"。
- 快捷键：1/2 硬币赢/输，3/4 先手/后手，5/6 决斗胜/负，Enter 保存。
- 备注框可选（例如对手或卡组），留空则不记录；保存后自动清空。

## 数据

- SQLite 数据库默认位于 `data/duels.db`，可用 `--db` 指定路径。
- 统计：当天与累计的硬币胜率、先手占比、决斗胜率、连串（当前/最长）。
- 图表标签页：按日硬币胜率趋势与每日对数。

## 测试

```bash
python -m unittest discover -s tests -v
```
