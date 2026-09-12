# 论文查重（第一次个人编程作业）

本项目从命令行读取原文、待检测论文和答案文件三个路径，将待检测文本相对于原文的重复率写入答案文件。程序只读取前两个指定文件，只写入第三个指定文件，不访问网络，也不扫描其他文件。

## 环境与运行

- Python 3.10 或更高版本
- 无第三方运行依赖

```powershell
python main.py C:\tests\orig.txt C:\tests\orig_add.txt C:\tests\ans.txt
```

三个路径按“原文、抄袭版、答案文件”的顺序传入。输出是 `0.00` 至 `1.00` 范围内的浮点比例，保留两位小数。`1.00` 表示待检测文本的全部二元组都能在原文中匹配；`0.00` 表示没有匹配的二元组。

中文文件优先按 UTF-8（含 BOM）读取，若解码失败则按 GB18030 尝试。答案以 UTF-8 写出。

## 算法

1. 使用 Unicode NFKC 统一全角字符，再进行大小写折叠。
2. 去掉空格、标点和符号，保留 Unicode 字母和数字。
3. 将文本切成连续字符二元组；文本太短时改用单字符。
4. 统计原文中每种片段的出现次数。逐个扫描待检测文本中的片段，每个原文片段最多匹配相同次数。
5. `重复率 = 匹配片段数 / 待检测文本片段总数`。

实现时间复杂度为 O(N+M)，空间复杂度为 O(U)，其中 N、M 是两份规范化文本长度，U 是原文中不同片段的数量。二元组多重集合对局部增删改较稳健，重复片段不会被无限重复计数。它不分析语义，也不惩罚片段换序；这是一种轻量级查重启发式算法，不能代替成熟的学术查重系统。

## 测试

```powershell
python -m unittest discover -s tests -v
```

覆盖了完全相同、截取、插入、空文本、无关文本、标点和空白、全角字符、短文本、重复片段上限、方向性、UTF-8 BOM、GB18030、文件错误和命令行行为等情况。

如需生成分支覆盖率报告，可安装可选开发工具 `coverage`：

```powershell
python -m pip install -r dev-requirements.txt
coverage run --branch -m unittest discover -s tests
coverage report -m
coverage html
```

浏览器打开 `htmlcov/index.html` 可截图保存覆盖率结果。该工具不参与提交程序的运行。

## 性能分析

可用内置 `cProfile` 对一段内存中的长文本进行剖析，无需额外依赖：

```powershell
python tools/profile_demo.py
python tools/performance_compare.py
```

第一条命令打印长文本样例规模、得分和 cProfile 函数统计；第二条命令将最终计数算法与仅供对比的两两扫描原型计时。计时结果受机器影响。也可用 `python -m cProfile -s tottime main.py ...` 分析课程样例。提交博客时请补上自己在指定 IDE/分析工具中的实际截图。

## 仓库目录

课程仓库中的项目目录为 `3124004049/`。仓库地址：<https://github.com/onychen/gdut-software-engineering-2026>。

发布博客前仍需依据本人实际投入填写 PSP 表格，并把性能分析和测试覆盖率截图插入博客；不要用估算值冒充实际耗时。
