# ssquant-ai 松鼠QuantAI策略开发助手

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![许可证](https://img.shields.io/badge/许可证-专有许可-red)
![logo](./ssquant/assets/squirrel_quant_logo.png)

一个基于AI的期货量化交易策略开发工具，结合人工智能与松鼠Quant量化交易框架，实现自然语言到可执行交易策略代码的转换。

## 🚀 功能特点

- **自然语言策略生成**：通过对话式交互，将您的交易想法转化为可执行的Python代码
- **一键式回测**：生成策略后可立即进行回测分析
- **实时交互**：支持流式输出，实时查看AI响应
- **灵活修改**：快速修改已生成的策略，调整参数和逻辑
- **丰富示例**：包含多种常见交易策略示例，便于学习和参考

## 📋 系统要求

- Python 3.8+
- Windows/macOS/Linux

## 🔧 安装方法

1. 克隆仓库
```bash
git clone https://github.com/songshuquant/ssquant-ai.git
cd ssquant-ai
```

2. 安装松鼠Quant框架
```bash
pip install ssquant
```

3. 安装项目依赖
```bash
pip install -r ai_cmd/requirements.txt
```

4. 配置环境变量
创建`ai_cmd/.env`文件，填入：

```dotenv
OPENAI_API_KEY="你的OpenAI密钥"
OPENAI_API_URL="https://api.openai.com/v1"  # 或您的API代理地址
GPT_MODEL="gpt-4o"  # 或其他支持的模型
```

## 🚀 快速开始

1. 启动程序
```bash
cd ai_cmd
python main.py
```

2. 输入策略描述
例如：`设计一个双均线交叉策略，5日均线上穿20日均线买入，下穿卖出，标的是螺纹钢主力合约`

3. 查看、运行及优化生成的策略

## 📖 使用指南


### 示例策略

项目的`examples`目录包含各种预设的量化交易策略示例：
- 双均线策略
- 海龟交易策略
- 强弱截面轮动策略
- 跨周期过滤策略
- 跨品种套利策略
- 机器学习策略
- 参数优化示例

## 📊 项目结构

```
├── ai_cmd/              # 主程序目录
│   ├── main.py          # 入口文件
│   ├── integration_module.py  # AI与回测框架集成
│   ├── backtest_engine.py     # 回测引擎封装
│   ├── gpt_client.py    # AI客户端
│   ├── workflow_manager.py    # 工作流管理
│   ├── code_parser.py   # 代码解析工具
│   ├── config.py        # 配置文件
│   └── requirements.txt # 依赖列表
├── data_cache/          # 数据缓存目录（包含模拟生成的示例数据）
│   ├── au888_*.csv      # 黄金期货模拟数据
│   ├── tick_data_*.csv  # Tick级别模拟数据
│   └── 生成模拟*.py      # 数据生成脚本
└── examples/            # 策略示例
    ├── 双均线策略.py
    ├── 海龟交易策略.py
    └── ...              # 其他示例
```

## 📝 许可证

本项目采用专有许可证 - 详情请查看 [LICENSE](LICENSE) 文件。商业使用需获得授权，请联系版权所有者：
- 邮箱：339093103@qq.com
- 网站：quant789.com

## 📢 免责声明

本工具仅用于教育和研究目的。生成的交易策略不构成投资建议，使用者应对自己的投资决策负全责。 
