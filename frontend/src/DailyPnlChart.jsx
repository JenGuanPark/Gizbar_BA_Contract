import React, { useMemo } from 'react';
import {
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Typography } from 'antd';

const { Text } = Typography;

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;

  const daily = payload.find(p => p.dataKey === 'daily_pnl');
  const cumulative = payload.find(p => p.dataKey === 'cumulative_pnl');

  return (
    <div style={{
      background: 'rgba(20, 20, 20, 0.95)',
      border: '1px solid #303030',
      borderRadius: 8,
      padding: '12px 16px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
      minWidth: 180,
    }}>
      <div style={{ color: '#888', fontSize: 12, marginBottom: 8 }}>{label}</div>
      {daily && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 4 }}>
          <Text style={{ color: '#aaa', fontSize: 13 }}>当日盈亏</Text>
          <Text strong style={{
            color: daily.value >= 0 ? '#00b96b' : '#ff4d4f',
            fontSize: 13,
          }}>
            {daily.value >= 0 ? '+' : ''}{daily.value.toFixed(2)} USDT
          </Text>
        </div>
      )}
      {cumulative && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24 }}>
          <Text style={{ color: '#aaa', fontSize: 13 }}>累计盈亏</Text>
          <Text strong style={{
            color: cumulative.value >= 0 ? '#00b96b' : '#ff4d4f',
            fontSize: 13,
          }}>
            {cumulative.value >= 0 ? '+' : ''}{cumulative.value.toFixed(2)} USDT
          </Text>
        </div>
      )}
    </div>
  );
};

const CustomLegend = () => (
  <div style={{ display: 'flex', gap: 20, justifyContent: 'flex-end', marginBottom: 8 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(0, 185, 107, 0.5)' }} />
      <Text style={{ color: '#888', fontSize: 12 }}>当日盈亏</Text>
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 20, height: 2, background: '#00b96b', borderRadius: 1 }} />
      <Text style={{ color: '#888', fontSize: 12 }}>累计曲线</Text>
    </div>
  </div>
);

const DailyPnlChart = ({ data = [] }) => {
  const processedData = useMemo(() => {
    if (!data.length) return [];
    return data.map(d => ({
      ...d,
      date: d.date.slice(5),
    }));
  }, [data]);

  const maxAbs = useMemo(() => {
    if (!processedData.length) return 100;
    return Math.max(...processedData.map(d => Math.abs(d.daily_pnl)), 1);
  }, [processedData]);

  if (!data.length) {
    return (
      <div style={{
        height: 280,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#444',
        fontSize: 13,
      }}>
        暂无历史盈亏数据
      </div>
    );
  }

  return (
    <div>
      <CustomLegend />
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={processedData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="cumulativeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00b96b" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#00b96b" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="cumulativeGradientNeg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff4d4f" stopOpacity={0} />
              <stop offset="95%" stopColor="#ff4d4f" stopOpacity={0.25} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1e1e1e"
            vertical={false}
          />

          <XAxis
            dataKey="date"
            tick={{ fill: '#555', fontSize: 11 }}
            axisLine={{ stroke: '#2a2a2a' }}
            tickLine={false}
            interval={Math.floor(processedData.length / 6)}
          />

          <YAxis
            yAxisId="bar"
            orientation="left"
            tick={{ fill: '#555', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => (v >= 0 ? `+${v}` : `${v}`)}
            domain={[-maxAbs * 1.3, maxAbs * 1.3]}
            width={55}
          />

          <YAxis
            yAxisId="line"
            orientation="right"
            tick={{ fill: '#555', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => (v >= 0 ? `+${v.toFixed(0)}` : `${v.toFixed(0)}`)}
            width={60}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <ReferenceLine yAxisId="bar" y={0} stroke="#303030" strokeWidth={1} />
          <ReferenceLine yAxisId="line" y={0} stroke="#303030" strokeWidth={1} />

          <Bar
            yAxisId="bar"
            dataKey="daily_pnl"
            radius={[3, 3, 0, 0]}
            maxBarSize={18}
            fill="#00b96b"
            shape={(props) => {
              const { x, y, width, height, value } = props;
              const isNeg = value < 0;
              return (
                <rect
                  x={x}
                  y={isNeg ? y + height : y}
                  width={width}
                  height={Math.abs(height)}
                  fill={isNeg ? 'rgba(255,77,79,0.55)' : 'rgba(0,185,107,0.55)'}
                  rx={3}
                />
              );
            }}
          />

          <Area
            yAxisId="line"
            type="monotone"
            dataKey="cumulative_pnl"
            stroke="#00b96b"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: '#00b96b', stroke: '#000', strokeWidth: 2 }}
            fill="url(#cumulativeGradient)"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DailyPnlChart;
