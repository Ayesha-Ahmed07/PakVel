// app/(tabs)/_layout.tsx
import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import React from "react";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#6C3BFF",
        tabBarInactiveTintColor: "#999",
      }}
    >
      {/* USER DASHBOARD */}
      <Tabs.Screen
        name="dashboard"
        options={{
          title: "My Trips",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="map-outline" color={color} size={size} />
          ),
        }}
      />

      {/* BROKER PACKAGES (USER SIDE) */}
      <Tabs.Screen
        name="brokers"
        options={{
          title: "Brokers",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="chat"
        options={{
          href:null,
        }}
      />
    </Tabs>
  );
}