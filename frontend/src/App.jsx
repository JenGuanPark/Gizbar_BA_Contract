import React, { useEffect, useState } from 'react';
import { Layout, Typography, Table, Card, Row, Col, Tag, Button, Alert, message, Popconfirm, Statistic, ConfigProvider, theme, Badge, Space, Empty } from 'antd';
import { 
  ReloadOutlined, 
  StopOutlined,
  WalletOutlined,
  RiseOutlined,
  FallOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined
} from '@ant-design/icons';
import axios from 'axios';
import zhCN from 'antd/locale/zh_CN';

const { Header, Content, Footer } = Layout;
const { Title, Text } = Typography;

// Read from Vercel environment variable or fallback to localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const App = () => {
  const [positions, setPositions] = useState([]);
  const [signals, setSignals] = useState([]);
  const [balance, setBalance] = useState({
    totalWalletBalance: 0,
    totalUnrealizedProfit: 0,
    totalMarginBalance: 0,
    availableBalance: 0,
    totalHistoryPnl: 0,
    is_demo: false
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const fetchData = async () => {
    // Skip polling if page is hidden to save API limit
    if (document.hidden) return;

    setLoading(true);
    // Don't clear error immediately to avoid flashing
    
    try {
      // Use Promise.allSettled to handle partial failures
      const results = await Promise.allSettled([
        axios.get(`${API_BASE_URL}/positions`),
        axios.get(`${API_BASE_URL}/signals`),
        axios.get(`${API_BASE_URL}/balance`)
      ]);

      const [posRes, sigRes, balRes] = results;

      if (posRes.status === 'fulfilled') {
        setPositions(posRes.value.data);
      }
      
      if (sigRes.status === 'fulfilled') {
        setSignals(sigRes.value.data);
      }

      if (balRes.status === 'fulfilled') {
        if (balRes.value.data && !balRes.value.data.error) {
          setBalance(balRes.value.data);
          // If we successfully got balance, clear any previous connection error
          setError(null);
        } else if (balRes.value.data && balRes.value.data.error) {
          // Backend returned specific error (e.g. API key invalid)
          console.error("Backend error:", balRes.value.data.error);
          // Only show error if it's critical, otherwise keep old data
        }
      } else {
        // Balance request failed (network error)
        console.error("Balance request failed");
      }

    } catch (err) {
      console.error(err);
      // Only set error if we really can't get data for a while
      // setError("无法连接后端服务，请检查服务是否启动。");
    } finally {
      setLoading(false);
    }
  };

  const handleClosePosition = async (symbol) => {
    setActionLoading(symbol);
    try {
      await axios.post(`${API_BASE_URL}/close-position`, {
        symbol: symbol,
        side: "CLOSE"
      });
      message.success(`成功平仓 ${symbol}`);
      fetchData(); 
    } catch (err) {
      message.error(`平仓失败: ${err.response?.data?.detail || err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  useEffect(() => {
    fetchData();
    // STOP AUTOMATIC POLLING to prevent IP ban (Error -1003)
    // Users must refresh manually for now until IP is unbanned
    // const interval = setInterval(fetchData, 10000); 
    
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // fetchData(); // Also disable auto-fetch on visibility change
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const positionColumns = [
    {
      title: '交易对',
      dataIndex: 'symbol',
      key: 'symbol',
      render: text => <Text strong style={{ fontSize: 16 }}>{text}</Text>,
    },
    {
      title: '方向',
      dataIndex: 'positionAmt',
      key: 'side',
      render: val => (
        <Tag color={val > 0 ? '#00b96b' : '#ff4d4f'} style={{ fontSize: 14, padding: '4px 8px' }}>
          {val > 0 ? '做多 Long' : '做空 Short'}
        </Tag>
      ),
    },
    {
      title: '持仓数量',
      dataIndex: 'positionAmt',
      key: 'positionAmt',
      render: val => Math.abs(val),
    },
    {
      title: '开仓均价',
      dataIndex: 'entryPrice',
      key: 'entryPrice',
      render: val => val.toFixed(4),
    },
    {
      title: '未实现盈亏 (USDT)',
      dataIndex: 'unRealizedProfit',
      key: 'unRealizedProfit',
      render: val => (
        <Text strong style={{ color: val >= 0 ? '#00b96b' : '#ff4d4f', fontSize: 16 }}>
          {val > 0 ? '+' : ''}{val.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '杠杆',
      dataIndex: 'leverage',
      key: 'leverage',
      render: val => <Tag color="gold">x{val}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="确认平仓"
          description={`确定要市价平掉 ${record.symbol} 吗?`}
          onConfirm={() => handleClosePosition(record.symbol)}
          okText="确定"
          cancelText="取消"
        >
          <Button 
            type="primary" 
            danger 
            size="small" 
            icon={<StopOutlined />}
            loading={actionLoading === record.symbol}
          >
            平仓
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const signalColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: val => <Text type="secondary">{new Date(val).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</Text>,
    },
    {
      title: '信号',
      key: 'signal',
      render: (_, record) => (
        <Space>
          <Text strong>{record.symbol}</Text>
          <Tag color={record.side === 'BUY' ? 'green' : 'red'}>
            {record.side === 'BUY' ? '多' : '空'}
          </Tag>
        </Space>
      ),
    },
    {
      title: '价格',
      dataIndex: 'entry_price',
      key: 'entry_price',
      render: val => val ? val : '市价',
    },
  ];

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#00b96b',
          colorBgContainer: '#1f1f1f',
          borderRadius: 8,
        },
      }}
    >
      <Layout style={{ minHeight: '100vh', background: '#000' }}>
        <Header style={{ 
          padding: '0 24px', 
          background: '#141414', 
          borderBottom: '1px solid #303030',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          height: 64
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <ThunderboltOutlined style={{ fontSize: 24, color: '#00b96b', marginRight: 12 }} />
            <Title level={4} style={{ color: 'white', margin: 0, letterSpacing: 1 }}>
              Gizbar <span style={{ color: '#00b96b' }}>智能跟单</span>
            </Title>
          </div>
          <Space>
             {balance.is_demo && (
                <Tag color="orange" icon={<SafetyCertificateOutlined />}>演示模式 (请配置API)</Tag>
             )}
             <Button type="text" icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={toggleFullscreen} style={{ color: '#888' }} title={isFullscreen ? "退出全屏" : "全屏模式"} />
             <Button type="text" icon={<ReloadOutlined />} onClick={fetchData} loading={loading} style={{ color: '#888' }}>
                刷新
             </Button>
             <Badge status="processing" text={<span style={{ color: '#00b96b' }}>运行中</span>} />
          </Space>
        </Header>

        <Content style={{ padding: '24px', margin: 0, minHeight: 280, flex: 1, overflowY: 'auto' }}>
          
          {error && <Alert message="连接错误" description={error} type="error" showIcon style={{ marginBottom: 24 }} />}

          {/* 资产仪表盘 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} md={4}>
              <Card bordered={false} bodyStyle={{ padding: '20px 24px' }}>
                <Statistic
                  title={<Text type="secondary">钱包总权益 (USDT)</Text>}
                  value={balance.totalWalletBalance}
                  precision={2}
                  valueStyle={{ color: '#fff', fontSize: 24, fontWeight: 'bold' }}
                  prefix={<WalletOutlined style={{ color: '#00b96b' }} />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={5}>
              <Card bordered={false} bodyStyle={{ padding: '20px 24px' }}>
                <Statistic
                  title={<Text type="secondary">历史总盈亏 (Realized PnL)</Text>}
                  value={balance.totalHistoryPnl}
                  precision={2}
                  valueStyle={{ color: balance.totalHistoryPnl >= 0 ? '#00b96b' : '#ff4d4f', fontSize: 24, fontWeight: 'bold' }}
                  prefix={balance.totalHistoryPnl >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  suffix={<span style={{ fontSize: 12, color: '#666', marginLeft: 4 }}>含手续费</span>}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={5}>
              <Card bordered={false} bodyStyle={{ padding: '20px 24px' }}>
                <Statistic
                  title={<Text type="secondary">未实现盈亏 (Unrealized)</Text>}
                  value={balance.totalUnrealizedProfit}
                  precision={2}
                  valueStyle={{ color: balance.totalUnrealizedProfit >= 0 ? '#00b96b' : '#ff4d4f', fontSize: 24, fontWeight: 'bold' }}
                  prefix={balance.totalUnrealizedProfit >= 0 ? <RiseOutlined /> : <FallOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={5}>
              <Card bordered={false} bodyStyle={{ padding: '20px 24px' }}>
                <Statistic
                  title={<Text type="secondary">可用保证金</Text>}
                  value={balance.availableBalance}
                  precision={2}
                  valueStyle={{ color: '#fff', fontSize: 24 }}
                  suffix={<span style={{ fontSize: 14, color: '#666' }}>USDT</span>}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={5}>
              <Card bordered={false} bodyStyle={{ padding: '20px 24px' }}>
                <Statistic
                  title={<Text type="secondary">当前持仓数</Text>}
                  value={positions.length}
                  valueStyle={{ color: '#fff', fontSize: 24 }}
                  suffix={<span style={{ fontSize: 14, color: '#666' }}>个</span>}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={24}>
            {/* 左侧：持仓列表 */}
            <Col xs={24} lg={16}>
              <Card 
                title={<Space><StopOutlined style={{ color: '#00b96b' }} />当前持仓监控</Space>} 
                bordered={false} 
                style={{ marginBottom: 24, minHeight: 500 }}
              >
                <Table 
                  columns={positionColumns} 
                  dataSource={positions} 
                  rowKey="symbol" 
                  pagination={false}
                  locale={{ emptyText: <Empty description="当前空仓，等待信号..." /> }}
                />
              </Card>
            </Col>

            {/* 右侧：信号日志 */}
            <Col xs={24} lg={8}>
              <Card 
                title={<Space><ThunderboltOutlined style={{ color: '#00b96b' }} />最新信号日志</Space>} 
                bordered={false}
                style={{ minHeight: 500 }}
              >
                <Table 
                  columns={signalColumns} 
                  dataSource={signals} 
                  rowKey="id" 
                  pagination={{ pageSize: 8, simple: true }}
                  size="small"
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无信号记录" /> }}
                />
              </Card>
            </Col>
          </Row>

        </Content>
        <Footer style={{ textAlign: 'center', background: '#000', color: '#444' }}>
          Gizbar Quant System ©2026 | Powered by Binance API
        </Footer>
      </Layout>
    </ConfigProvider>
  );
};

export default App;
