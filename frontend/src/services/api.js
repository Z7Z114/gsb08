import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,
});

export const processMeeting = async (audioFile, designData) => {
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('designData', JSON.stringify(designData));
  
  const response = await api.post('/process-meeting', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getMeetings = async () => {
  const response = await api.get('/meetings');
  return response.data;
};

export const getMeeting = async (meetingId) => {
  const response = await api.get(`/meetings/${meetingId}`);
  return response.data;
};

export const sendEmail = async (meetingId, recipients) => {
  const response = await api.post(`/send-email/${meetingId}`, { recipients });
  return response.data;
};

export const getPatterns = async () => {
  const response = await api.get('/patterns');
  return response.data;
};

export const getDyes = async () => {
  const response = await api.get('/dyes');
  return response.data;
};

export const calculateCost = async (params) => {
  const response = await api.post('/cost-calculator', params);
  return response.data;
};

export default api;
