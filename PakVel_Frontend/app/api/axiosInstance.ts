import axios from "axios";
import { Platform } from "react-native";

/**
 * Determine the correct API base URL depending on where the app is running:
 *  - Web (browser): backend on same computer → http://127.0.0.1:8000
 *  - Mobile (Expo Go on same Wi-Fi): backend on your laptop's IP → http://192.168.x.x:8000
 *
 * ⚠️ To find your IP:
 *   → Open CMD → type "ipconfig"
 *   → Copy the IPv4 Address (e.g. 192.168.10.6)       my data IP:  10.124.161.176
 */
const LOCAL_IP = "192.168.18.66"; 

const API_BASE_URL =
  Platform.OS === "android" || Platform.OS === "ios"
    ? `http://${LOCAL_IP}:8000` // for phone (Expo Go)
    : "http://127.0.0.1:8000";  // for web browser (on same PC)

/**
 * Create a reusable Axios instance for all API requests.
 * Automatically adds JSON headers and allows us to include JWT tokens later.
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Optional: Automatically attach JWT token to requests if it exists in AsyncStorage
import AsyncStorage from "@react-native-async-storage/async-storage";

api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;