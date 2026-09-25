import React, { useState } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Select, 
  InputNumber, 
  Button, 
  Upload, 
  message, 
  Spin,
  Divider,
  Space,
  Typography,
  Tag,
  Table,
  Alert
} from 'antd';
import { 
  UploadOutlined, 
  SendOutlined, 
  PlayCircleOutlined,
  MailOutlined,
  CalculatorOutlined
} from '@ant-design/icons';
import { processMeeting, calculateCost, sendEmail } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const MeetingProcessor = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [result, setResult] = useState(null);
  const [costResult, setCostResult] = useState(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const navigate = useNavigate();

  const beforeUpload = (file) => {
    const isAudio = file.type.startsWith('audio/');
    if (!isAudio) {
      message.error('请上传音频文件！');
      return false;
    }
    const isLt1G = file.size / 1024 / 1024 < 1000;
    if (!isLt1G) {
      message.error('音频文件大小不能超过1GB！');
      return false;
    }
    setAudioFile(file);
    return false;
  };

  const handleSubmit = async (values) => {
    if (!audioFile) {
      message.error('请先上传会议录音文件！');
      return;
    }

    setLoading(true);
    try {
      const designData = {
        series_name: values.series_name,
        fabric_type: values.fabric_type,
        complexity: values.complexity,
        quantity: values.quantity,
        notes: values.notes,
      };

      const response = await processMeeting(audioFile, designData);
      setResult(response);
      message.success('会议处理完成！');
    } catch (error) {
      message.error('处理失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCalculateCost = async () => {
    const values = form.getFieldsValue();
    try {
      const cost = await calculateCost({
        fabric_type: values.fabric_type,
        complexity: values.complexity,
        quantity: values.quantity || 1,
      });
      setCostResult(cost);
      message.success('成本计算完成！');
    } catch (error) {
      message.error('计算失败：' + error.message);
    }
  };

  const handleSendEmail = async () => {
    if (!result) return;
    setEmailLoading(true);
    try {
      await sendEmail(result.meeting_id, []);
      message.success('邮件已发送给买手店！');
    } catch (error) {
      message.error('发送失败：' + error.message);
    } finally {
      setEmailLoading(false);
    }
  };

  const costColumns = [
    {
      title: '项目',
      dataIndex: 'item',
      key: 'item',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '成本（元）',
      dataIndex: 'cost',
      key: 'cost',
      render: (text) => <Text type="success">¥{text}</Text>,
    },
    {
      title: '占比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
  ];

  const costData = costResult ? [
    { item: '面料成本', cost: costResult.fabric_cost, percentage: costResult.fabric_percentage },
    { item: '染料成本', cost: costResult.dye_cost, percentage: costResult.dye_percentage },
    { item: '人工成本', cost: costResult.labor_cost, percentage: costResult.labor_percentage },
    { item: '水电能耗', cost: costResult.utility_cost, percentage: costResult.utility_percentage },
    { item: '其他费用', cost: costResult.other_cost, percentage: costResult.other_percentage },
  ] : [];

  return (
    <div>
      <Title level={3} style={{ color: '#1e3a5f', marginTop: 0 }}>
        <PlayCircleOutlined /> 会议处理中心
      </Title>
      <Paragraph type="secondary">
        上传会议录音，系统将自动进行降噪处理、语音识别、说话人分离，并生成专业会议纪要。
      </Paragraph>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <Card title="会议信息录入" bordered={false} style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              fabric_type: 'cotton',
              complexity: 'medium',
              quantity: 1,
            }}
          >
            <Form.Item
              label="会议录音"
              required
            >
              <Upload
                beforeUpload={beforeUpload}
                maxCount={1}
                accept="audio/*"
                showUploadList={true}
              >
                <div className="upload-zone">
                  <UploadOutlined style={{ fontSize: 48, color: '#2d5a87' }} />
                  <p style={{ marginTop: 16, color: '#1e3a5f', fontWeight: 500 }}>
                    点击或拖拽上传会议录音
                  </p>
                  <p style={{ color: '#666', fontSize: 12 }}>
                    支持 WAV、MP3、M4A 等格式，最大 1GB
                  </p>
                </div>
              </Upload>
              {audioFile && (
                <Tag color="blue" style={{ marginTop: 8 }}>
                  已选择：{audioFile.name}
                </Tag>
              )}
            </Form.Item>

            <Form.Item
              name="series_name"
              label="系列名称"
              rules={[{ required: true, message: '请输入系列名称' }]}
            >
              <Input placeholder="例如：2024春夏靛蓝手工扎染系列" />
            </Form.Item>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <Form.Item
                name="fabric_type"
                label="面料类型"
              >
                <Select>
                  <Option value="cotton">纯棉</Option>
                  <Option value="linen">亚麻</Option>
                  <Option value="silk">真丝</Option>
                  <Option value="wool">羊毛</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="complexity"
                label="工艺复杂度"
              >
                <Select>
                  <Option value="simple">简单</Option>
                  <Option value="medium">中等</Option>
                  <Option value="complex">复杂</Option>
                </Select>
              </Form.Item>
            </div>

            <Form.Item
              name="quantity"
              label="预估产量（件）"
            >
              <InputNumber min={1} max={10000} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              name="notes"
              label="补充说明"
            >
              <TextArea rows={3} placeholder="记录设计方向、目标客户、定价区间等信息..." />
            </Form.Item>

            <Space>
              <Button type="primary" htmlType="submit" loading={loading} size="large">
                <PlayCircleOutlined /> 开始处理
              </Button>
              <Button onClick={handleCalculateCost} size="large">
                <CalculatorOutlined /> 预计算成本
              </Button>
            </Space>
          </Form>
        </Card>

        <Card 
          title="处理结果" 
          bordered={false} 
          style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
          extra={result && (
            <Space>
              <Button 
                type="primary" 
                icon={<MailOutlined />} 
                onClick={handleSendEmail}
                loading={emailLoading}
              >
                发送给买手店
              </Button>
              <Button onClick={() => navigate(`/meeting/${result.meeting_id}`)}>
                查看详情
              </Button>
            </Space>
          )}
        >
          <Spin spinning={loading} tip="正在处理音频，可能需要几分钟...">
            {result ? (
              <div>
                <Alert
                  message="处理完成"
                  description={`系列主题：${result.summary.series_theme}`}
                  type="success"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <Divider orientation="left">识别的工艺模式</Divider>
                <Space wrap style={{ marginBottom: 16 }}>
                  {result.patterns.tie_methods.map((m, i) => (
                    <Tag key={i} color="geekblue">{m}</Tag>
                  ))}
                  {result.patterns.color_mentions.map((c, i) => (
                    <Tag key={i} color="cyan">{c}</Tag>
                  ))}
                </Space>

                <Divider orientation="left">会议摘要</Divider>
                <div 
                  className="markdown-content"
                  style={{ 
                    maxHeight: 400, 
                    overflowY: 'auto',
                    padding: 16,
                    background: '#fafafa',
                    borderRadius: 8
                  }}
                >
                  {result.summary.summary}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
                <PlayCircleOutlined style={{ fontSize: 64, color: '#e0e0e0' }} />
                <p style={{ marginTop: 16 }}>上传音频并填写信息后点击开始处理</p>
                <p style={{ fontSize: 12 }}>
                  系统将自动完成：librosa降噪 → Whisper识别 → pyannote分离 → OpenAI摘要
                </p>
              </div>
            )}
          </Spin>
        </Card>
      </div>

      {costResult && (
        <Card 
          title="成本核算预览" 
          bordered={false} 
          style={{ marginTop: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
            <Table
              columns={costColumns}
              dataSource={costData}
              pagination={false}
              size="small"
            />
            <div style={{ 
              padding: 24, 
              background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
              borderRadius: 8,
              color: 'white',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: 14, opacity: 0.8, marginBottom: 8 }}>总成本</div>
              <div style={{ fontSize: 36, fontWeight: 'bold', marginBottom: 16 }}>
                ¥{costResult.total_cost}
              </div>
              <div style={{ fontSize: 14, opacity: 0.8, marginBottom: 8 }}>建议零售价</div>
              <div style={{ fontSize: 28, fontWeight: 'bold', color: '#ffd700' }}>
                ¥{costResult.suggested_retail}
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default MeetingProcessor;
