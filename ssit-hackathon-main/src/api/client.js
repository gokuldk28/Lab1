import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export const USER_ID_KEY = "finsight_user_id";

export function getUserId() {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = "9999999999";
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

export function setUserId(id) {
  localStorage.setItem(USER_ID_KEY, id);
}

export async function analyzeExpenses(userId, budget = null) {
  const { data } = await api.post("/analyze-expenses", {
    user_id: userId,
    budget,
  });
  return data;
}

export async function getTransactions(userId) {
  const { data } = await api.get("/get-transactions", { params: { user_id: userId } });
  return data;
}

export async function predictSpending(userId, horizon_days = 14) {
  const { data } = await api.post("/predict-spending", { user_id: userId, horizon_days });
  return data;
}

export async function chatInsights(userId, message, history = []) {
  const { data } = await api.post("/chat-insights", {
    user_id: userId,
    message,
    history,
  });
  return data;
}

export async function addTransaction(payload) {
  const { data } = await api.post("/transactions", payload);
  return data;
}

export async function updateBudget(userId, budget) {
  const { data } = await api.post("/budget", { user_id: userId, budget });
  return data;
}

export async function importBank(userId, count = 10) {
  const { data } = await api.post("/import-bank", { user_id: userId, count });
  return data;
}

export default api;
