import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";

export default function BrokerTabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#6C3BFF",
        tabBarInactiveTintColor: "#999",
      }}
    >
      

      <Tabs.Screen
        name="brokerDashboard"
        options={{
          title: "My Packages",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="albums-outline" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="incoming"
        options={{
          title: "Requests",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="chatbubble-outline" color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}