import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Tag, Typography, Empty, Spin, Table, Modal } from 'antd';
import { BgColorsOutlined, EnvironmentOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { getDyes } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const DyeLibrary = () => {
  const [dyes, setDyes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDye, setSelectedDye] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    loadDyes();
  }, []);

  const loadDyes = async () => {
    try {
      const data = await getDyes();
      setDyes(data);
    } catch (error) {
      console.error('Failed to load dyes:', error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '色样',
      dataIndex: 'color',
      key: 'color',
      width: 80,
      render: (color) => (
        <div 
          style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 6, 
            background: color,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
          }} 
        />
      ),
    },
    {
      title: '染料名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => { setSelectedDye(record); setModalVisible(true); }}>
          {text}
        </a>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
    },
    {
      title: '产地',
      dataIndex: 'origin',
      key: 'origin',
      render: (text) => (
        <span><EnvironmentOutlined style={{ marginRight: 4 }} />{text}</span>
      ),
    },
    {
      title: '特性',
      dataIndex: 'properties',
      key: 'properties',
      render: (props) => (
        <span>
          {props.map((p, i) => (
            <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{p}</Tag>
          ))}
        </span>
      ),
    },
    {
      title: '价格',
      dataIndex: 'price_per_kg',
      key: 'price_per_kg',
      render: (price) => <Text strong style={{ color: '#1e3a5f' }}>¥{price}/kg</Text>,
    },
  ];

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
        <BgColorsOutlined /> 植物染料色谱
      </Title>
      <Paragraph type="secondary">
        精选来自全国各地的天然植物靛蓝染料，每一种都有其独特的色彩性格和工艺要求。
      </Paragraph>

      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        {dyes.map((dye) => (
          <Col xs={24} sm={12} md={8} lg={8} xl={4} key={dye.id}>
            <Card
              className="pattern-card"
              hoverable
              bordered={false}
              style={{ borderRadius: 12, overflow: 'hidden', height: '100%' }}
              bodyStyle={{ padding: 20 }}
              onClick={() => { setSelectedDye(dye); setModalVisible(true); }}
            >
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <div 
                  style={{ 
                    width: '100%', 
                    height: 100, 
                    borderRadius: 8,
                    background: dye.color,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    margin: '0 auto 12px'
                  }} 
                />
                <Text strong style={{ fontSize: 16, color: '#1e3a5f', display: 'block' }}>
                  {dye.name}
                </Text>
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  {dye.origin}
                </div>
              </div>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>特性：</Text>
                <div style={{ marginTop: 4 }}>
                  {dye.properties.slice(0, 2).map((p, i) => (
                    <Tag key={i} color="blue" size="small">{p}</Tag>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                <div style={{ fontSize: 12, color: '#999' }}>
                  <ThunderboltOutlined /> {dye.temperature}
                </div>
                <Text strong style={{ color: '#2d5a87' }}>¥{dye.price_per_kg}</Text>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="详细参数表" bordered={false} style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
        <Table
          columns={columns}
          dataSource={dyes}
          pagination={false}
          rowKey="id"
        />
      </Card>

      <Modal
        title={selectedDye?.name}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedDye && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24, marginBottom: 24 }}>
              <div 
                style={{ 
                  height: 180, 
                  borderRadius: 12,
                  background: selectedDye.color,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
                }} 
              />
              <div>
                <Title level={4} style={{ marginTop: 0, color: '#1e3a5f' }}>
                  {selectedDye.name}
                </Title>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#2d5a87', marginBottom: 12 }}>
                  ¥{selectedDye.price_per_kg}/kg
                </div>
                <Paragraph style={{ marginBottom: 16 }}>
                  {selectedDye.source}
                </Paragraph>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">产地：</Text>
                  <span><EnvironmentOutlined style={{ marginRight: 4 }} />{selectedDye.origin}</span>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary">PH值范围：</Text>
                  <Text strong>{selectedDye.ph_range}</Text>
                </div>
                <div>
                  <Text type="secondary">最佳温度：</Text>
                  <Text strong>{selectedDye.temperature}</Text>
                </div>
              </div>
            </div>
            <Divider style={{ margin: '12px 0' }} />
            <div>
              <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>主要特性：</Text>
              <div>
                {selectedDye.properties.map((p, i) => (
                  <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{p}</Tag>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DyeLibrary;
