from ssquant.backtest.backtest_core import MultiSourceBacktester
import pandas as pd
import numpy as np
import os
import sys
from ssquant.api.strategy_api import StrategyAPI
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')

g_last_position = 0
g_last_model_update = 0

def initialize(api: StrategyAPI):
    """
    策略初始化函数
    
    Args:
        api: 策略API对象
    """
    global g_last_position, g_last_model_update
    
    api.log("机器学习策略（随机森林）初始化...")
    api.log("所有交易将使用下一根K线开盘价执行 (order_type='next_bar_open')")
    api.log("本策略使用随机森林模型预测价格走势")
    
    # 策略参数
    lookback_period = api.get_param('lookback_period', 60)  # 回溯期
    prediction_threshold = api.get_param('prediction_threshold', 0.6)  # 预测阈值
    min_training_samples = api.get_param('min_training_samples', 30)  # 最小训练样本数
    
    api.log(f"回溯期: {lookback_period}天")
    api.log(f"预测阈值: {prediction_threshold}")
    api.log(f"最小训练样本数: {min_training_samples}")
    
    # 初始化全局状态变量
    g_last_position = 0
    g_last_model_update = 0

# 技术指标计算函数
def calculate_features(df):
    """计算特征函数，从K线数据计算各种技术指标"""
    # 确保df是DataFrame类型并且含有必要的列
    if not isinstance(df, pd.DataFrame) or not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
        raise ValueError("输入数据必须是包含OHLCV数据的DataFrame")
    
    # 复制数据，避免修改原始数据
    df_features = df.copy()
    
    # 计算移动平均线
    df_features['ma5'] = df['close'].rolling(window=5).mean()
    df_features['ma10'] = df['close'].rolling(window=10).mean()
    df_features['ma20'] = df['close'].rolling(window=20).mean()
    df_features['ma60'] = df['close'].rolling(window=60).mean()
    
    # 计算均线差值和比例
    df_features['ma5_10_diff'] = df_features['ma5'] - df_features['ma10']
    df_features['ma5_20_diff'] = df_features['ma5'] - df_features['ma20']
    df_features['ma10_20_diff'] = df_features['ma10'] - df_features['ma20']
    df_features['ma5_ma10_ratio'] = df_features['ma5'] / df_features['ma10']
    df_features['ma5_ma20_ratio'] = df_features['ma5'] / df_features['ma20']
    
    # 计算价格变化率
    df_features['price_change'] = df['close'].pct_change()
    df_features['price_change_1d'] = df['close'].pct_change(periods=1)
    df_features['price_change_5d'] = df['close'].pct_change(periods=5)
    df_features['price_change_10d'] = df['close'].pct_change(periods=10)
    
    # 计算波动率指标
    df_features['volatility_5d'] = df['close'].rolling(window=5).std()
    df_features['volatility_10d'] = df['close'].rolling(window=10).std()
    
    # 计算相对高低位
    df_features['high_low_diff'] = df['high'] - df['low']
    df_features['high_close_diff'] = df['high'] - df['close']
    df_features['low_close_diff'] = df['close'] - df['low']
    
    # 计算成交量指标
    df_features['volume_ma5'] = df['volume'].rolling(window=5).mean()
    df_features['volume_ma10'] = df['volume'].rolling(window=10).mean()
    df_features['volume_ratio'] = df['volume'] / df_features['volume_ma5'].replace(0, np.nan)
    
    # 计算RSI指标
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)  # 避免除以零
    df_features['rsi14'] = 100 - (100 / (1 + rs))
    
    # 计算MACD指标
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df_features['macd'] = ema12 - ema26
    df_features['macd_signal'] = df_features['macd'].ewm(span=9, adjust=False).mean()
    df_features['macd_hist'] = df_features['macd'] - df_features['macd_signal']
    
    # 计算布林带指标
    df_features['boll_mid'] = df['close'].rolling(window=20).mean()
    df_features['boll_std'] = df['close'].rolling(window=20).std()
    df_features['boll_upper'] = df_features['boll_mid'] + 2 * df_features['boll_std']
    df_features['boll_lower'] = df_features['boll_mid'] - 2 * df_features['boll_std']
    df_features['boll_width'] = (df_features['boll_upper'] - df_features['boll_lower']) / df_features['boll_mid'].replace(0, np.nan)
    
    # 计算价格相对于布林带的位置
    boll_range = df_features['boll_upper'] - df_features['boll_lower']
    df_features['boll_position'] = (df['close'] - df_features['boll_lower']) / boll_range.replace(0, np.nan)
    
    # 向前填充数据，避免NaN值
    df_features = df_features.fillna(method='ffill')
    
    return df_features

def generate_target(df, forward_period=5):
    """
    生成标签：未来n个周期的价格变动方向
    
    Args:
        df: 股票数据DataFrame
        forward_period: 未来预测的周期数
        
    Returns:
        包含标签的DataFrame
    """
    df = df.copy()
    
    # 计算未来n个周期的价格变动
    df['future_return'] = df['close'].shift(-forward_period) / df['close'] - 1
    
    # 生成分类标签：1表示上涨，0表示下跌
    df['target'] = np.where(df['future_return'] > 0, 1, 0)
    
    return df

def train_model(klines, model_path='ml_model.pkl', min_samples=30, api=None):
    """
    训练随机森林模型并保存
    
    Args:
        klines: K线数据
        model_path: 模型保存路径
        min_samples: 最小样本数
        api: 策略API对象，用于记录日志
        
    Returns:
        训练好的模型数据字典或None（如果训练失败）
    """
    try:
        # 确保使用绝对路径
        if not os.path.isabs(model_path):
            model_path = os.path.join(os.getcwd(), model_path)
            
        # 计算特征
        if api:
            api.log("计算训练特征...")
        df = calculate_features(klines)
        
        # 生成标签
        df = generate_target(df, forward_period=5)
        
        # 删除NaN值
        df_clean = df.dropna().copy()
        
        # 检查样本数量
        if len(df_clean) < min_samples:
            if api:
                api.log(f"训练样本不足: {len(df_clean)}/{min_samples}")
            return None
            
        if api:
            api.log(f"有效训练样本数: {len(df_clean)}")
        
        # 选择特征和标签
        feature_columns = [
            'ma5_10_diff', 'ma5_20_diff', 'ma10_20_diff', 
            'ma5_ma10_ratio', 'ma5_ma20_ratio',
            'price_change', 'price_change_1d', 'price_change_5d', 'price_change_10d',
            'volatility_5d', 'volatility_10d',
            'high_low_diff', 'high_close_diff', 'low_close_diff',
            'volume_ratio', 'rsi14',
            'macd', 'macd_signal', 'macd_hist',
            'boll_width', 'boll_position'
        ]
        
        X = df_clean[feature_columns]
        y = df_clean['target']
        
        # 标准化数据
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 训练随机森林模型
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42
        )
        model.fit(X_scaled, y)
        
        # 计算训练集准确率
        train_predictions = model.predict(X_scaled)
        accuracy = np.mean(train_predictions == y)
        if api:
            api.log(f"模型训练集准确率: {accuracy:.4f}")
        
        # 保存模型和缩放器
        model_data = {
            'model': model,
            'scaler': scaler,
            'feature_columns': feature_columns
        }
        
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
        
        joblib.dump(model_data, model_path)
        if api:
            api.log(f"模型已保存到: {model_path}")
        
        return model_data
        
    except Exception as e:
        if api:
            api.log(f"模型训练失败: {str(e)}")
        return None

def predict_with_model(model_data, new_data, api=None):
    """
    使用训练好的模型进行预测
    
    Args:
        model_data: 包含模型、缩放器和特征列的字典
        new_data: 新的K线数据
        api: 策略API对象，用于记录日志
        
    Returns:
        预测结果（上涨概率）或None（如果预测失败）
    """
    try:
        if model_data is None:
            if api:
                api.log("模型数据为空，无法预测")
            return None
            
        # 提取模型、缩放器和特征列
        model = model_data['model']
        scaler = model_data['scaler']
        feature_columns = model_data['feature_columns']
        
        # 计算特征
        df_features = calculate_features(new_data)
        
        # 删除NaN值
        df_features = df_features.dropna()
        
        if df_features.empty:
            if api:
                api.log("处理后的特征数据为空，无法预测")
            return None
        
        # 检查是否包含所有所需特征
        missing_features = [f for f in feature_columns if f not in df_features.columns]
        if missing_features:
            if api:
                api.log(f"缺少特征: {missing_features}")
            return None
        
        # 提取最新的特征数据
        latest_features = df_features.iloc[-1][feature_columns]
        
        # 检查特征是否有NaN
        if latest_features.isna().any():
            if api:
                api.log("最新特征含有NaN值，无法预测")
            return None
            
        latest_features_array = latest_features.values.reshape(1, -1)
        
        # 标准化特征
        latest_features_scaled = scaler.transform(latest_features_array)
        
        # 预测上涨概率
        prediction_proba = model.predict_proba(latest_features_scaled)[0][1]
        
        return prediction_proba
        
    except Exception as e:
        if api:
            api.log(f"预测过程发生错误: {str(e)}")
        return None

def machine_learning_strategy(api: StrategyAPI):
    """
    机器学习策略：使用随机森林模型预测价格走势
    
    该策略使用多种技术指标作为特征，训练随机森林模型预测未来价格变动，并根据预测结果进行交易。
    
    策略逻辑：
    1. 收集足够的历史数据用于特征计算
    2. 在初始阶段，使用历史数据训练随机森林模型
    3. 使用训练好的模型预测未来价格走势
    4. 当预测上涨概率大于阈值时，开多仓
    5. 当预测下跌概率大于阈值时，开空仓
    """
    global g_last_position, g_last_model_update
    
    # 确保至少有1个数据源
    if not api.require_data_sources(1):
        return
    
    # 获取参数
    lookback_period = api.get_param('lookback_period', 60)  # 回溯期
    prediction_threshold = api.get_param('prediction_threshold', 0.6)  # 预测阈值
    model_update_frequency = api.get_param('model_update_frequency', 20)  # 模型更新频率
    min_training_samples = api.get_param('min_training_samples', 30)  # 最小训练样本数
    
    # 获取当前索引和日期时间
    bar_idx = api.get_idx(0)
    bar_datetime = api.get_datetime(0)
    
    # 获取K线数据
    klines = api.get_klines(0)
    
    # 确保有足够的数据
    if len(klines) < lookback_period:
        api.log(f"数据不足，需要至少 {lookback_period} 条K线，当前只有 {len(klines)} 条")
        return
    
    # 每100个bar打印一次状态
    if bar_idx % 100 == 0:
        api.log(f"当前处理：{bar_datetime}, 索引：{bar_idx}, 数据长度：{len(klines)}")
    
    # 模型文件路径
    model_path = os.path.join(os.getcwd(), 'ml_model.pkl')
    
    # 判断是否需要更新模型
    need_model_update = (
        bar_idx >= lookback_period and 
        (bar_idx == lookback_period or  # 首次达到回溯期
         bar_idx - g_last_model_update >= model_update_frequency)  # 已经过了更新周期
    )
    
    model_data = None
    
    # 更新模型
    if need_model_update:
        api.log(f"正在训练/更新随机森林模型... (bar_idx={bar_idx})")
        model_data = train_model(
            klines.iloc[:bar_idx+1], 
            model_path=model_path,
            min_samples=min_training_samples,
            api=api
        )
        
        if model_data:
            api.log("模型训练/更新成功")
            g_last_model_update = bar_idx
        else:
            api.log("模型训练/更新失败，尝试加载现有模型")
    
    # 如果没有更新模型或更新失败，尝试加载现有模型
    if model_data is None:
        try:
            if os.path.exists(model_path):
                model_data = joblib.load(model_path)
                api.log("成功加载现有模型")
            else:
                api.log("模型文件不存在，无法加载")
        except Exception as e:
            api.log(f"加载模型失败: {str(e)}")
    
    # 如果没有模型数据，无法进行预测
    if model_data is None:
        api.log("无可用模型，跳过预测")
        return
    
    # 使用模型进行预测
    if bar_idx >= lookback_period:
        # 进行预测
        prediction_proba = predict_with_model(model_data, klines.iloc[:bar_idx+1], api)
        
        # 如果预测失败，返回
        if prediction_proba is None:
            api.log("预测失败，无法交易")
            return
            
        # 获取当前价格和持仓
        current_price = api.get_price(0)
        current_pos = api.get_pos(0)
        
        # 每10个bar打印一次预测结果
        if bar_idx % 10 == 0 or current_pos != g_last_position:
            api.log(f"预测上涨概率：{prediction_proba:.4f}, 当前价格：{current_price:.2f}, 当前持仓：{current_pos}")
        
        # 交易逻辑
        if prediction_proba > prediction_threshold:  # 预测上涨
            if current_pos <= 0:  # 如果当前没有多仓或者持有空仓
                # 先平掉空仓
                if current_pos < 0:
                    api.log(f"预测上涨概率 {prediction_proba:.4f} > {prediction_threshold}，平空仓")
                    api.buycover(order_type='next_bar_open')
                
                # 开多仓
                api.log(f"预测上涨概率 {prediction_proba:.4f} > {prediction_threshold}，开多仓")
                api.buy(volume=1, order_type='next_bar_open')
                
        elif prediction_proba < (1 - prediction_threshold):  # 预测下跌
            if current_pos >= 0:  # 如果当前没有空仓或者持有多仓
                # 先平掉多仓
                if current_pos > 0:
                    api.log(f"预测下跌概率 {1-prediction_proba:.4f} > {prediction_threshold}，平多仓")
                    api.sell(order_type='next_bar_open')
                
                # 开空仓
                api.log(f"预测下跌概率 {1-prediction_proba:.4f} > {prediction_threshold}，开空仓")
                api.sellshort(volume=1, order_type='next_bar_open')
        
        # 更新上一次持仓状态
        g_last_position = current_pos

if __name__ == "__main__":
    # 导入API认证信息
    try:
        from ssquant.config.auth_config import get_api_auth
        API_USERNAME, API_PASSWORD = get_api_auth()
    except ImportError:
        print("警告：未找到 API_USERNAME, API_PASSWORD账户密码，请在上方get_api_auth()里面填写松鼠Quant俱乐部的账户密码")

    # 创建回测器
    backtester = MultiSourceBacktester()
    
    # 设置基础配置
    backtester.set_base_config({
        'username': API_USERNAME,
        'password': API_PASSWORD,
        'use_cache': True,
        'save_data': True,
        'align_data': False,
        'fill_method': 'ffill',
        'debug': True
    })
    
    # 添加数据源配置
    backtester.add_symbol_config(
        symbol='rb888', 
        config={  # 螺纹钢期货配置
            'start_date': '2022-01-01',  # 延长回测时间，确保有足够训练数据
            'end_date': '2025-06-1',
            'initial_capital': 100000.0,
            'commission': 0.0003,
            'margin_rate': 0.1,
            'contract_multiplier': 10,
            'periods': [
                {'kline_period': '1d', 'adjust_type': '1'},  # 日K线
            ]
    })
    
    # 策略参数
    strategy_params = {
        'lookback_period': 60,           # 回溯期
        'prediction_threshold': 0.6,     # 预测阈值
        'model_update_frequency': 20,    # 模型更新频率
        'min_training_samples': 30       # 最小训练样本数
    }
    
    # 运行回测
    results = backtester.run(
        strategy=machine_learning_strategy,
        initialize=initialize,
        strategy_params=strategy_params
    )
    