// app/(broker-tabs)/incoming.tsx

import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  FlatList,
  Image,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";
import styled from "styled-components/native";
import { api } from "../api/axiosInstance";

/* ---------------- TYPES ---------------- */
type IncomingRequest = {
  tripId: string;
  travelerName: string;
  destination: string;
  budget: number;
  status: "chatting" | "active" | "completion_pending" | "completed";
  tripType?: string;
};

/* ---------------- BACKGROUND ---------------- */
const BackgroundPattern = styled.View`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
`;

export default function IncomingRequestsScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<IncomingRequest[]>([]);

  const handleComplete = async (tripId: string) => {
  try {
    const token = await AsyncStorage.getItem("token");

    await api.patch(
      `/trips/${tripId}/complete`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    alert("Completion recorded");

    // update UI instantly
    setRequests((prev) =>
      prev.map((r) =>
        r.tripId === tripId
          ? { ...r, status: "completed" }
          : r
      )
    );

  } catch (err) {
    alert("Failed to confirm");
  }
};

  useEffect(() => {
    const fetchIncomingRequests = async () => {
      const token = await AsyncStorage.getItem("token");

      const res = await api.get("/broker/incoming-requests", {
        headers: { Authorization: `Bearer ${token}` },
      });

      setRequests(res.data);
      setLoading(false);
    };

    fetchIncomingRequests();
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6C3BFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Background */}
      <BackgroundPattern>
        <Image
          source={require("../../assets/images/pattern.jpg")}
          style={{ width: "100%", height: "100%" }}
          resizeMode="cover"
        />
        <View style={styles.overlay} />
      </BackgroundPattern>

      {/* HEADER */}
      <LinearGradient
        colors={["#6C3BFF", "#9333EA"]}
        style={styles.header}
      >
        <TouchableOpacity onPress={() => router.replace("/brokerDashboard")}>
          <MaterialIcons name="arrow-back" size={26} color="white" />
        </TouchableOpacity>

        <Text style={styles.headerTitle}>Incoming Requests</Text>
      </LinearGradient>

      {/* LIST */}
      <FlatList
        data={requests}
        keyExtractor={(item) => item.tripId}
        contentContainerStyle={{ padding: 20, paddingBottom: 100 }}
        renderItem={({ item, index }) => {
          const isAI =
            item.tripType === "ai_self" ||
            item.tripType === "ai_broker";

          const initial =
            item.travelerName?.charAt(0).toUpperCase() || "T";

          return (
            <TouchableOpacity
              activeOpacity={0.9}
              style={styles.card}
              onPress={() => router.push(`/chat/${item.tripId}`)}
            >
              {/* Rank Badge */}
              <View style={styles.rankBadge}>
                <Text style={styles.rankText}>#{index + 1}</Text>
              </View>

              {/* Header Row */}
              <View style={styles.topRow}>
                {/* Avatar */}
                <LinearGradient
                  colors={["#6C3BFF", "#9333EA"]}
                  style={styles.avatar}
                >
                  <Text style={styles.avatarText}>{initial}</Text>
                </LinearGradient>

                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.name}>
                    {item.travelerName}
                  </Text>

                  <Text style={styles.destination}>
                    📍 {item.destination}
                  </Text>
                </View>

                {/* Trip Type Badge */}
                <View
                  style={[
                    styles.typeBadge,
                    isAI ? styles.aiBadge : styles.brokerBadge,
                  ]}
                >
                  <Text style={styles.badgeText}>
                    {isAI ? "AI Trip" : "Broker Trip"}
                  </Text>
                </View>
              </View>

{item.status === "completion_pending" &&  (
  <TouchableOpacity
    onPress={() => handleComplete(item.tripId)}
    style={{
      backgroundColor: "#F59E0B",
      padding: 10,
      borderRadius: 12,
      marginTop: 12,
      alignItems: "center",
    }}
  >
    <Text style={{ color: "white", fontWeight: "700" }}>
      Trip ended — Confirm Completion
    </Text>
  </TouchableOpacity>
)}

              {/* Bottom Row */}
              <View style={styles.bottomRow}>
                {/* Budget Pill */}
                <View style={styles.budgetPill}>
                  <Text style={styles.budgetText}>
                    💰 PKR {item.budget || 0}
                  </Text>
                </View>

                {/* Status Badge */}
                <View
                  style={[
                    styles.statusBadge,
                    item.status === "active"
                      ? styles.active
                      : item.status === "completion_pending"
                      ? {backgroundColor: "#FEF3C7"}
                      : styles.chatting,
                  ]}
                >
                  <Text style={styles.statusText}>
                    {item.status === "active"
                      ? "Active"
                      : item.status === "completion_pending"
                      ? "Pending"
                      : "Chatting"}
                  </Text>
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

/* ---------------- STYLES ---------------- */

const styles = StyleSheet.create({
  container: { flex: 1 },

  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(15,23,42,0.35)",
  },

  header: {
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },

  headerTitle: {
    textAlign: "center",
    color: "white",
    fontSize: 22,
    fontWeight: "800",
  },

  card: {
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 26,
    padding: 20,
    marginBottom: 25,
    elevation: 12,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 14,
    position: "relative",
  },

  rankBadge: {
    position: "absolute",
    top: -10,
    right: -10,
    backgroundColor: "#F59E0B",
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },

  rankText: {
    color: "white",
    fontWeight: "800",
  },

  topRow: {
    flexDirection: "row",
    alignItems: "center",
  },

  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    justifyContent: "center",
    alignItems: "center",
  },

  avatarText: {
    color: "white",
    fontSize: 18,
    fontWeight: "800",
  },

  name: {
    fontSize: 18,
    fontWeight: "800",
  },

  destination: {
    marginTop: 4,
    fontSize: 14,
    color: "#4B5563",
  },

  typeBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 14,
  },

  aiBadge: {
    backgroundColor: "#DBEAFE",
  },

  brokerBadge: {
    backgroundColor: "#DCFCE7",
  },

  badgeText: {
    fontSize: 12,
    fontWeight: "700",
  },

  bottomRow: {
    marginTop: 18,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  budgetPill: {
    backgroundColor: "#F1F5F9",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 18,
  },

  budgetText: {
    fontWeight: "700",
    color: "#1E293B",
  },

  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
  },

  chatting: {
    backgroundColor: "#E0E7FF",
  },

  active: {
    backgroundColor: "#DCFCE7",
  },

  statusText: {
    fontSize: 12,
    fontWeight: "700",
  },
});