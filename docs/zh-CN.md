# envlayer-audit：分层环境配置审计

[English](../README.md) · [Русский](ru.md) · [Deutsch](de.md)

工具展示每个配置键来自哪一层、在哪一行被覆盖，并检查配置策略。
它不输出配置值，不修改文件，也不会将配置加载进进程环境。
需要 Python 3.10 或更新版本；从仓库运行不需要安装依赖。

## 快速开始

在仓库根目录执行：

```sh
python -m envlayer_audit examples/base.env examples/production.env --policy examples/policy.json
python -m envlayer_audit examples/base.env examples/production.env --format json
python -m unittest discover -s tests -v
```

文件参数按优先级从低到高排列。`L1` 表示第一个文件，冒号后为行号。
示例输出中的 `LOG_LEVEL: L1:4 -> L2:1 (1 overrides)` 表示第二层覆盖了第一层。
最后一次有效赋值生效；同一文件中的重复赋值也算覆盖。
即使两次赋值相同，也计为覆盖，因为工具不比较配置值。
不会自动寻找 `.env` 文件，也不读取 `NODE_ENV`。

可选安装命令为 `python -m pip install .`，随后可用 `envlayer-audit`。
安装需要 setuptools 77+，pip 可能下载构建工具；项目尚未发布到 PyPI。

## 策略文件

将以下内容保存为 UTF-8 JSON 文件，通过 `--policy` 传入：

```json
{"required":["REGION"],"allowed":["REGION","LOG_LEVEL"],"protected":["REGION"]}
```

- `required`：必须存在的键；空值也算存在。
- `allowed`：允许出现的全部键。省略时不限制；空列表禁止任何键。
- `protected`：在所有层中最多赋值一次，同一文件中的重复也违规。
  此规则不要求键存在，如需存在请同时加入 `required`。

键名区分大小写，不支持通配符。未知字段、重复列表项、重复 JSON 字段、
无效键名以及不在 `allowed` 中的必需键均导致策略错误。
解析任意赋值失败时，报告 `complete: false`，跳过全部策略检查并失败。
此时的键来源只是部分结果，不能视为有效的最终配置。

## 语法与边界

支持无 BOM 的 UTF-8、LF/CRLF、空行、`#` 注释、可选 `export`、
`KEY=value`，键名为 `[A-Za-z_][A-Za-z0-9_]*`。
支持单行裸值、单引号或双引号值和空值。双引号内反斜杠用于识别转义字符；
单引号不支持转义。闭合引号后只允许空白或空白分隔的注释。
裸值中不能有引号，也不能以反斜杠结尾。不支持多行值、续行、只有键的声明。
不执行命令，不展开变量，不解码值。这不是完整的 dotenv 或 shell 解析器。
详细规范及库接口见英文 README。

退出码：`0` 通过；`1` 语法或策略违规；`2` 文件读取、UTF-8、策略或参数错误。
读取及策略加载失败时，即使选择 JSON，也会在 stderr 输出通用错误。
策略超过 JSON 解析器的嵌套深度限制时，同样以 `2` 退出并输出此通用错误，
不输出堆栈跟踪或路径。

报告会显示有效键名和行号，但不显示文件路径、值或值的哈希。
不要把秘密放在键名中；输入仍会存在进程内存中。大文件整体读入内存。
报告不能替代应用实际加载器的测试。示例仅含虚构值。
贡献前请运行测试，并阅读 [贡献指南](../CONTRIBUTING.md) 和
[安全说明](../SECURITY.md)。使用 [MIT 许可证](../LICENSE)。
