# 可视化原始数据模板

## 雷达图 CSV

使用宽表。第一列固定为 `competitor`，其余数值列为动态评分维度。

```csv
competitor,简单易用,功能完整度,智能化水平,差异化竞争力
Apple,5,4,4,4
Huawei,4,5,4,4
Xiaomi,4,4,3,3
```

评分依据等非评分字段不要混入该 CSV，单独放在评分依据表中。

## 四象限 / 矩阵定位图 CSV

```csv
competitor,x,y,bubble,x_label,y_label,manual_confirmation
Apple,4.8,4.0,80,简单易用,功能深度,false
Huawei,4.2,4.7,90,简单易用,功能深度,false
Xiaomi,4.0,3.9,70,简单易用,功能深度,true
```

`bubble` 对四象限图可选；对矩阵定位/气泡图可作为第三维数据。

## 评分依据表

```markdown
| 竞品 | 维度 | 分数 | 评分依据 | 证据状态 |
|---|---|---:|---|---|
| Huawei | 功能完整度 | 5 | ... | A |
| Apple | 专业深度 | 3 | ... | B / 请人工确认 |
```

## 重生成命令

```bash
python scripts/charts/generate_charts.py --input radar.csv --type radar --output-dir out
python scripts/charts/generate_charts.py --input xy.csv --type quadrant --output-dir out
python scripts/charts/generate_charts.py --input xy.csv --type matrix --output-dir out
python scripts/charts/generate_charts.py --input radar.csv --xy-input xy.csv --type all --output-dir out
```
