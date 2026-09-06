import AsyncStorage from "@react-native-async-storage/async-storage";
import { router, Stack } from "expo-router";
import { useEffect } from "react";

export default function RootLayout() {
  useEffect(() => {
    const checkLogin = async () => {
      const token = await AsyncStorage.getItem("token");
      const role = await AsyncStorage.getItem("role");

      if (!token) return; // let user see welcome screen

      if (role === "broker") {
        router.replace("/brokerDashboard");
      } else {
        router.replace("/dashboard");
      }
    };

    checkLogin();
  }, []);

  return <Stack screenOptions={{ headerShown: false }} />;
}