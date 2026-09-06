import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  ImageBackground,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { api } from "./api/axiosInstance";

export default function BrokerProfile() {
  const router = useRouter();

  const [profile, setProfile] = useState<any>({});
  const [reviews, setReviews] = useState<any[]>([]);
  useEffect(() => {
    loadBrokerInfo();
    loadReviews(); 
  }, []);

  const loadBrokerInfo = async () => {
    try {
      const token = await AsyncStorage.getItem("token");
      const res = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile(res.data);
    } catch (e) {
      console.log("Profile error:", e);
    }
  };
  const loadReviews = async () => {
    try {
      const token = await AsyncStorage.getItem("token");

      const res = await api.get("/reviews/broker-reviews", {
        headers: { Authorization: `Bearer ${token}` },
      });

      setReviews(res.data.reviews || []);
    } catch (e) {
      console.log("Reviews error:", e);
    }
  };

  const initials =
    profile.full_name?.charAt(0)?.toUpperCase() ||
    profile.email?.charAt(0)?.toUpperCase() ||
    "?";

  return (
    <ImageBackground
      source={require("../assets/images/pattern.jpg")}
      style={{ flex: 1 }}
      resizeMode="cover"
    >
      <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>

        {/* HEADER */}
        <LinearGradient colors={["#58C7FF", "#6C3BFF"]} style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <MaterialIcons name="arrow-back" size={26} color="white" />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>My Account</Text>
        </LinearGradient>

        {/* CONTENT */}
        <ScrollView contentContainerStyle={styles.container}>

          {/* PROFILE CARD */}
          <View style={styles.card}>
            <View style={styles.avatarWrapper}>
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarText}>{initials}</Text>
              </View>
            </View>

            <Text style={styles.nameText}>{profile.full_name || "No Name"}</Text>
            <Text style={styles.emailText}>{profile.email || "Not Available"}</Text>
          </View>

          {/* 🔥 REVIEWS CARD (REPLACES ANALYTICS) */}
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Customer Reviews</Text>

            {reviews.length === 0 ? (
              <Text style={styles.note}>No reviews yet.</Text>
            ) : (
              reviews.map((r, index) => (
                <View key={index} style={styles.reviewCard}>
                  
                  {/* Rating */}
                  <Text style={styles.rating}>⭐ {r.rating}/5</Text>

                  {/* Comment */}
                  <Text style={styles.comment}>
                    {r.comment || "No comment provided"}
                  </Text>

                  {/* User + Date */}
                  <Text style={styles.reviewMeta}>
                    — {r.user} • {new Date(r.created_at).toLocaleDateString()}
                  </Text>

                </View>
              ))
            )}
          </View>

        </ScrollView>
      </LinearGradient>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 55,
    paddingBottom: 22,
    alignItems: "center",
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
  },

  backButton: {
    position: "absolute",
    left: 20,
    top: 55,
  },

  headerTitle: {
    color: "white",
    fontSize: 22,
    fontWeight: "700",
  },

  container: {
    padding: 20,
    paddingBottom: 80,
  },

  /* ENHANCED CARD */
  card: {
    backgroundColor: "white",
    padding: 25,
    borderRadius: 18,
    marginBottom: 20,

    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 3,
  },

  /* Avatar Circle */
  avatarWrapper: {
    alignItems: "center",
    marginBottom: 15,
  },
  avatarCircle: {
    width: 90,
    height: 90,
    borderRadius: 90,
    backgroundColor: "#6C3BFF",
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: {
    color: "white",
    fontSize: 36,
    fontWeight: "900",
  },

  nameText: {
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
    color: "#333",
    marginTop: 5,
  },

  emailText: {
    fontSize: 15,
    textAlign: "center",
    color: "#555",
    marginTop: 4,
  },

  /* Analytics Section */
  sectionTitle: {
    fontSize: 19,
    fontWeight: "700",
    color: "#6C3BFF",
    marginBottom: 10,
  },

  label: {
    fontSize: 15,
    color: "#444",
    marginTop: 5,
  },

  viewsCount: {
    fontSize: 38,
    fontWeight: "900",
    color: "#6C3BFF",
    marginTop: 6,
  },

  note: {
    marginTop: 6,
    fontSize: 14,
    color: "#666",
  },
   reviewCard: {
    backgroundColor: "#F8F7FF",
    padding: 12,
    borderRadius: 10,
    marginTop: 10,
  },

  rating: {
    fontSize: 16,
    fontWeight: "700",
    color: "#6C3BFF",
  },

  comment: {
    marginTop: 4,
    fontSize: 14,
    color: "#333",
  },

  reviewMeta: {
    marginTop: 6,
    fontSize: 12,
    color: "#777",
  },
});