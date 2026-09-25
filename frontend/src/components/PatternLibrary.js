import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Tag, Typography, Empty, Spin, Modal, Button } from 'antd';
import { AppstoreOutlined, ThunderboltOutlined, EyeOutlined } from '@ant-design/icons';
import { getPatterns } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const difficultyColors = {
  '简单': 'green',
  '中等': 'orange',
  '复杂': 'red',
};

const PatternLibrary = () => {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    loadPatterns();
  }, []);

  const loadPatterns = async () => {
    try {
      const data = await getPatterns();
      setPatterns(data);
    } catch (error) {
      console.error('Failed to load patterns:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPatternSvg = (pattern) => {
    const patterns = {
      '云纹扎': (
        <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
          <defs>
            <radialGradient id="cloudGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#4a7a9e" />
              <stop offset="50%" stopColor="#2d5a87" />
              <stop offset="100%" stopColor="#1e3a5f" />
            </radialGradient>
          </defs>
          <circle cx="100" cy="100" r="90" fill="url(#cloudGrad)" />
          <path d="M20,100 Q50,60 100,100 T180,100" stroke="rgba(255,255,255,0.3)" strokeWidth="3" fill="none" />
          <path d="M20,120 Q50,80 100,120 T180,120" stroke="rgba(255,255,255,0.2)" strokeWidth="2" fill="none" />
          <path d="M20,80 Q50,40 100,80 T180,80" stroke="rgba(255,255,255,0.25)" strokeWidth="2" fill="none" />
        </svg>
      ),
      '水波纹': (
        <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="waveGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3d6e99" />
              <stop offset="100%" stopColor="#1e3a5f" />
            </linearGradient>
          </defs>
          <rect width="200" height="200" fill="url(#waveGrad)" />
          {[30, 60, 90, 120, 150, 170].map((y, i) => (
            <path 
              key={i}
              d={`M0,${y} Q50,${y-15} 100,${y} T200,${y}`}
              stroke="rgba(255,255,255,0.2)"
              strokeWidth="2"
              fill="none"
            />
          ))}
        </svg>
      ),
      '几何菱格': (
        <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
          <defs>
            <pattern id="geoPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <rect width="40" height="40" fill="#2d5a87" />
              <polygon points="20,0 40,20 20,40 0,20" fill="#1e3a5f" stroke="#4a7a9e" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="200" height="200" fill="url(#geoPattern)" />
        </svg>
      ),
      '冰裂纹': (
        <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
          <rect width="200" height="200" fill="#1e3a5f" />
          {Array.from({ length: 30 }).map((_, i) => {
            const x1 = Math.random() * 200;
            const y1 = Math.random() * 200;
            const x2 = x1 + (Math.random() - 0.5) * 60;
            const y2 = y1 + (Math.random() - 0.5) * 60;
            return (
              <line 
                key={i}
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke="rgba(255,255,255,0.4)"
                strokeWidth="1"
              />
            );
          })}
        </svg>
      ),
      '螺旋纹': (
        <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
          <defs>
            <radialGradient id="spiralGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#4a7a9e" />
              <stop offset="100%" stopColor="#1a2f4a" />
            </radialGradient>
          </defs>
          <circle cx="100" cy="100" r="90" fill="url(#spiralGrad)" />
          {Array.from({ length: 4 }).map((_, i) => {
            const r = 20 + i * 20;
            return (
              <circle 
                key={i}
                cx="100" cy="100" r={r}
                fill="none"
                stroke="rgba(255,255,255,0.3)"
                strokeWidth="3"
                strokeDasharray={`${Math.PI * r / 8} ${Math.PI * r / 16}`}
              />
            );
          })}
        </svg>
      ),
      '花瓣纹': (
        <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
          <defs>
            <radialGradient id="petalGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#5a8ab8" />
              <stop offset="100%" stopColor="#1e3a5f" />
            </radialGradient>
          </defs>
          <circle cx="100" cy="100" r="90" fill="url(#petalGrad)" />
          {Array.from({ length: 6 }).map((_, i) => {
            const angle = (i * 60) * Math.PI / 180;
            const x = 100 + Math.cos(angle) * 50;
            const y = 100 + Math.sin(angle) * 50;
            return (
              <ellipse 
                key={i}
                cx={x} cy={y} rx="25" ry="40"
                transform={`rotate(${i * 60} ${x} ${y})`}
                fill="rgba(255,255,255,0.15)"
                stroke="rgba(255,255,255,0.3)"
                strokeWidth="1"
              />
            );
          })}
          <circle cx="100" cy="100" r="15" fill="rgba(255,255,255,0.3)" />
        </svg>
      ),
    };
    return patterns[pattern.name] || (
      <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%' }}>
        <rect width="200" height="200" fill="#2d5a87" />
        <text x="100" y="110" textAnchor="middle" fill="white" fontSize="14">
          {pattern.name}
        </text>
      </svg>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ color: '#1e3a5f', marginTop: 0 }}>
        <AppstoreOutlined /> 图案设计库
      </Title>
      <Paragraph type="secondary">
        探索传统与现代结合的扎染图案，每种图案都标注了工艺难度和推荐染色次数。
      </Paragraph>

      {patterns.length === 0 ? (
        <Empty description="暂无图案数据" />
      ) : (
        <Row gutter={[24, 24]}>
          {patterns.map((pattern) => (
            <Col xs={24} sm={12} md={8} lg={8} xl={6} key={pattern.id}>
              <Card
                className="pattern-card"
                hoverable
                bordered={false}
                style={{ borderRadius: 12, overflow: 'hidden' }}
                bodyStyle={{ padding: 0 }}
                onClick={() => {
                  setSelectedPattern(pattern);
                  setModalVisible(true);
                }}
              >
                <div style={{ height: 180, background: '#f0f4f8' }}>
                  {getPatternSvg(pattern)}
                </div>
                <div style={{ padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 16, color: '#1e3a5f' }}>{pattern.name}</Text>
                    <Tag color={difficultyColors[pattern.difficulty]}>{pattern.difficulty}</Tag>
                  </div>
                  <Paragraph 
                    ellipsis={{ rows: 2 }} 
                    style={{ marginBottom: 12, color: '#666', fontSize: 13 }}
                  >
                    {pattern.description}
                  </Paragraph>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Tag color="blue">{pattern.technique}</Tag>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      <ThunderboltOutlined /> 染色 {pattern.dye_count} 次
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title={selectedPattern?.name}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>,
          <Button key="use" type="primary">
            <EyeOutlined /> 在设计中使用
          </Button>,
        ]}
        width={700}
      >
        {selectedPattern && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div style={{ height: 300, background: '#f0f4f8', borderRadius: 8, overflow: 'hidden' }}>
              {getPatternSvg(selectedPattern)}
            </div>
            <div>
              <Title level={4} style={{ marginTop: 0, color: '#1e3a5f' }}>
                {selectedPattern.name}
              </Title>
              <Paragraph>{selectedPattern.description}</Paragraph>
              <Divider style={{ margin: '12px 0' }} />
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">工艺手法：</Text>
                <Tag color="blue" style={{ marginLeft: 8 }}>{selectedPattern.technique}</Tag>
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">难度等级：</Text>
                <Tag color={difficultyColors[selectedPattern.difficulty]} style={{ marginLeft: 8 }}>
                  {selectedPattern.difficulty}
                </Tag>
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">推荐染色次数：</Text>
                <Text strong style={{ marginLeft: 8 }}>{selectedPattern.dye_count} 次</Text>
              </div>
              <div>
                <Text type="secondary">标签：</Text>
                <div style={{ marginTop: 8 }}>
                  {selectedPattern.tags.map((tag, i) => (
                    <Tag key={i}>{tag}</Tag>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PatternLibrary;
