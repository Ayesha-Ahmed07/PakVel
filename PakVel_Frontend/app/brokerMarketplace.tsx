export const unstable_settings = { ssr: false };

import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
    ActivityIndicator,
    Alert,
    ImageBackground,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";
import { api } from "./api/axiosInstance";

export default function BrokerMarketplace() {
  const router = useRouter();
  const { itineraryId, destination, budget } = useLocalSearchParams();

  const [brokers, setBrokers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingTripFor, setCreatingTripFor] = useState<string | null>(null);

  useEffect(() => {
    loadMarketplace();
  }, []);

  const loadMarketplace = async () => {
    try {
      const token = await AsyncStorage.getItem("token");

      const res = await api.get("/broker/marketplace", {
        headers: { Authorization: `Bearer ${token}` },
      });

      const sorted = res.data.sort(
        (a: any, b: any) => b.rating - a.rating
      );

      setBrokers(sorted);
    } catch (err) {
      console.log("Marketplace error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDiscuss = async (broker: any) => {
    try {
      setCreatingTripFor(broker.broker_id);
      const token = await AsyncStorage.getItem("token");

      const res = await api.post(
        "/trips/",
        {
          itinerary_id: itineraryId,
          trip_type: "ai_broker",
          broker_id: broker.broker_id,
          destination,
          budget,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      router.push(`/chat/${res.data.trip_id}`);
    } catch (err: any) {
      Alert.alert(
        "Error",
        err.response?.data?.detail || "Unable to start discussion."
      );
    } finally {
      setCreatingTripFor(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6C3BFF" />
      </View>
    );
  }

  return (
    <ImageBackground
      source={require("../assets/images/dashboard-bg.jpg")}
      style={{ flex: 1 }}
      imageStyle={{ opacity: 0.95 }}
    >
      <LinearGradient colors={["#0F172A", "#1E293B"]} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.container}>
          <Text style={styles.header}>Broker Marketplace</Text>

          {brokers.map((broker, index) => {
            const isCreating =
              creatingTripFor === broker.broker_id;
            const initial =
              broker.org_name?.charAt(0).toUpperCase() || "B";

            return (
              <View
                key={broker.broker_id}
                style={styles.card}
              >
                {/* Ranking */}
                <View style={styles.rankBadge}>
                  <Text style={styles.rankText}>
                    #{index + 1}
                  </Text>
                </View>

                {/* Header */}
                <View style={styles.headerRow}>
                  <LinearGradient
                    colors={["#6C3BFF", "#9333EA"]}
                    style={styles.avatar}
                  >
                    <Text style={styles.avatarText}>
                      {initial}
                    </Text>
                  </LinearGradient>

                  <View style={{ flex: 1, marginLeft: 12 }}>
                    <Text style={styles.orgName}>
                      {broker.org_name}
                    </Text>

                    {/* Tagline */}
                    {broker.tagline ? (
                      <Text style={styles.tagline}>
                        {broker.tagline}
                      </Text>
                    ) : null}

                    {/* Experience Badge */}
                    <View style={styles.experienceBadge}>
                      <MaterialIcons
                        name="workspace-premium"
                        size={14}
                        color="#6C3BFF"
                      />
                      <Text style={styles.expText}>
                        {broker.years_of_experience} Years
                        Experience
                      </Text>
                    </View>
                  </View>
                </View>

                {/* Specializations */}
                {broker.specialized_areas?.length > 0 && (
                  <View style={styles.chipContainer}>
                    {broker.specialized_areas.map(
                      (area: string, i: number) => (
                        <View key={i} style={styles.chip}>
                          <Text style={styles.chipText}>
                            {area}
                          </Text>
                        </View>
                      )
                    )}
                  </View>
                )}

                {/* Stats */}
                <View style={styles.statsRow}>
                  <View style={styles.statBox}>
                    <Text style={styles.statNumber}>
                      {broker.rating}
                    </Text>
                    <Text style={styles.statLabel}>
                      Rating
                    </Text>
                  </View>

                  <View style={styles.statBox}>
                    <Text style={styles.statNumber}>
                      {broker.review_count}
                    </Text>
                    <Text style={styles.statLabel}>
                      Reviews
                    </Text>
                  </View>

                  <View style={styles.statBox}>
                    <Text style={styles.statNumber}>
                      {broker.total_itineraries}
                    </Text>
                    <Text style={styles.statLabel}>
                      Trips
                    </Text>
                  </View>
                </View>

                {/* CTA */}
                <TouchableOpacity
                  style={styles.discussBtn}
                  onPress={() => handleDiscuss(broker)}
                  disabled={isCreating}
                >
                  {isCreating ? (
                    <ActivityIndicator color="white" />
                  ) : (
                    <>
                      <MaterialIcons
                        name="chat"
                        size={20}
                        color="white"
                      />
                      <Text style={styles.discussText}>
                        Discuss Trip Plan
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            );
          })}
        </ScrollView>
      </LinearGradient>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingTop: 80,
    paddingBottom: 60,
  },

  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  header: {
    fontSize: 28,
    fontWeight: "900",
    color: "white",
    marginBottom: 30,
    textAlign: "center",
  },

  card: {
    backgroundColor: "rgba(255,255,255,0.97)",
    borderRadius: 24,
    padding: 20,
    marginBottom: 30,
    elevation: 8,
    position: "relative",
  },

  rankBadge: {
    position: "absolute",
    top: -12,
    right: -12,
    backgroundColor: "#F59E0B",
    borderRadius: 16,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },

  rankText: {
    color: "white",
    fontWeight: "800",
  },

  headerRow: {
    flexDirection: "row",
    alignItems: "center",
  },

  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: "center",
    alignItems: "center",
  },

  avatarText: {
    color: "white",
    fontWeight: "800",
    fontSize: 18,
  },

  orgName: {
    fontSize: 20,
    fontWeight: "800",
  },

  tagline: {
    fontSize: 13,
    color: "#6B7280",
    marginTop: 4,
  },

  experienceBadge: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
    backgroundColor: "#EEF2FF",
    alignSelf: "flex-start",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },

  expText: {
    fontSize: 12,
    fontWeight: "600",
    marginLeft: 4,
    color: "#6C3BFF",
  },

  chipContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 12,
  },

  chip: {
    backgroundColor: "#F1F5F9",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 14,
    marginRight: 8,
    marginBottom: 8,
  },

  chipText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#334155",
  },

  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 16,
  },

  statBox: {
    alignItems: "center",
    flex: 1,
  },

  statNumber: {
    fontSize: 18,
    fontWeight: "800",
  },

  statLabel: {
    fontSize: 12,
    color: "#64748B",
    marginTop: 2,
  },

  discussBtn: {
    marginTop: 20,
    backgroundColor: "#6C3BFF",
    paddingVertical: 14,
    borderRadius: 18,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },

  discussText: {
    color: "white",
    fontWeight: "800",
    fontSize: 16,
  },
});