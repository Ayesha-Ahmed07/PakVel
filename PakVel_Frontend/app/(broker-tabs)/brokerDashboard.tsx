//brokerDashboard.tsx
import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Alert,
  Animated, Easing,
  Image,
  ImageBackground,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
  ViewStyle,
} from "react-native";
import { ActivityIndicator, Card, Text } from "react-native-paper";
import { api } from "../api/axiosInstance";

// TYPES
interface BrokerItinerary {
  _id: string;
  title: string;
  location: string;
  duration_days: number;
  price_per_person: number;
  cover_image?: string;
  is_published: boolean;
}

interface BrokerProfile {
  name?: string;
  email?: string;
}

export default function BrokerDashboard() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [itineraries, setItineraries] = useState<BrokerItinerary[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profile, setProfile] = useState<BrokerProfile>({});
  const menuAnim = useState(new Animated.Value(0))[0];  

  useEffect(() => {
    loadMyItineraries();
    //loadProfile();
  }, []);

  useEffect(() => {
    Animated.timing(menuAnim, { toValue: menuOpen ? 1 : 0,
duration:250,
easing: Easing.out(Easing.ease),
useNativeDriver: false,
    }).start();
  }, [menuOpen]);

  // LOAD ITINERARIES
  const loadMyItineraries = async () => {
    try {
      const token = await AsyncStorage.getItem("token");
      const res = await api.get("/broker/show-itineraries", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setItineraries(res.data || []);
    } catch (err) {
      console.log("Dashboard load error:", err);
    } finally {
      setLoading(false);
    }
  };

  // LOAD PROFILE
  // const loadProfile = async () => {
  //   try {
  //     const token = await AsyncStorage.getItem("token");
  //     const res = await api.get("/broker/profile", {
  //       headers: { Authorization: `Bearer ${token}` },
  //     });
  //     setProfile(res.data);
  //   } catch (error) {
  //     console.log("Profile error:", error);
  //   }
  // };

  // LOGOUT
  const logout = async () => {
    await AsyncStorage.removeItem("token");
    router.replace("/login");
  };

  if (loading) {
    return (
      <LinearGradient colors={["#A7D8FF", "#7F6CFF"]} style={styles.centered}>
        <ActivityIndicator size="large" color="white" />
        <Text style={{ color: "white", marginTop: 10 }}>Loading...</Text>
      </LinearGradient>
    );
  }

  return (
    <ImageBackground
      source={require("../../assets/images/pattern.jpg")}
      style={{ flex: 1,
        width: "100%",
        height: "100%",
       }}
      resizeMode="cover"
      imageStyle={{ width: "100%",
          height: "100%",
          resizeMode: "cover",
          opacity: 0.99, }}
    >
      <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>

        {/* ------------------ HEADER ------------------ */}
        <LinearGradient colors={["#58C7FF", "#6C3BFF"]} style={styles.header}>
          
          {/* MENU BUTTON */}
          <TouchableOpacity
            style={styles.menuBtn}
            onPress={() => setMenuOpen(!menuOpen)}
          >
            <MaterialIcons name="menu" size={30} color="white" />
          </TouchableOpacity>

          <Text style={styles.heading}>Pakvel</Text>

          {/* LOGOUT BUTTON */}
          <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
            <MaterialIcons name="logout" size={28} color="white" />
          </TouchableOpacity>
        </LinearGradient>

        {/* -------- DROPDOWN MENU -------- */}
        {/* -------- SMOOTH SLIDE-DOWN GLASS MENU -------- */}
<Animated.View
  style={[
    styles.animatedMenu,
    {
      height: menuAnim.interpolate({
        inputRange: [0, 1],
        outputRange: [0, 180], // menu height animation
      }),
      opacity: menuAnim,
    },
  ]}
>
  <BlurView intensity={40} tint="light" style={styles.glassMenu}>
    
    <TouchableOpacity
      style={styles.menuItem}
      onPress={() => {
        setMenuOpen(false);
        router.push("/brokerProfile");
      }}
    >
      <MaterialIcons name="person" size={22} color="#fff" />
      <Text style={styles.menuItemText}>My Account</Text>
    </TouchableOpacity>

    <TouchableOpacity
      style={styles.menuItem}
      onPress={() => {
        setMenuOpen(false);
        router.push("/brokerContactInfo");
      }}
    >
      <MaterialIcons name="contact-phone" size={22} color="#fff" />
      <Text style={styles.menuItemText}>Contact Info</Text>
    </TouchableOpacity>

    <TouchableOpacity
      style={styles.menuItem}
      onPress={() => Alert.alert("Coming Soon", "Password change screen.")}
    >
      <MaterialIcons name="settings" size={22} color="#fff" />
      <Text style={styles.menuItemText}>Settings</Text>
    </TouchableOpacity>

  </BlurView>
</Animated.View>

        {/* ------------------ MAIN CONTENT ------------------ */}
        <ScrollView contentContainerStyle={styles.content}>
          <Text style={styles.sectionTitle}>My Itineraries</Text>

          {itineraries.map((item) => (
            <TouchableOpacity
              key={item._id}
              onPress={() =>
                router.push({
                  pathname: "/brokerViewItinerary",
                  params: { id: item._id },
                })
              }
            >
              <Card style={styles.card}>
                <Image
                  source={
                    item.cover_image
                      ? { uri: item.cover_image }
                      : require("../../assets/images/sample-trip.png")
                  }
                  style={styles.cardImage}
                />
                <Card.Content>
                  <Text style={styles.cardTitle}>{item.title}</Text>
                  <Text style={styles.cardSub}>
                    {item.location} • {item.duration_days} days
                  </Text>
                  <Text style={styles.cardPrice}>
                    PKR {item.price_per_person}
                  </Text>

                  <View style={statusBadge(item.is_published)}>
                    <Text style={styles.statusText}>
                      {item.is_published ? "Published" : "Draft"}
                    </Text>
                  </View>
                </Card.Content>
              </Card>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* ---------------- FAB BUTTON ---------------- */}
        <TouchableOpacity
          style={styles.fab}
          onPress={() => router.push("/brokerAddItinerary")}
        >
          <MaterialIcons name="add" size={30} color="white" />
        </TouchableOpacity>

      </LinearGradient>
    </ImageBackground>
  );
}

/* ---------------- STYLES ---------------- */
const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },

  header: {
    paddingTop: 48,
    paddingBottom: 18,
    alignItems: "center",
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },

  heading: { color: "white", fontSize: 26, fontWeight: "800" },

  menuBtn: {
    position: "absolute",
    left: 18,
    top: 50,
  },

  logoutBtn: {
    position: "absolute",
    right: 20,
    top: 50,
  },

  dropdownMenu: {
    backgroundColor: "white",
    marginHorizontal: 15,
    marginTop: 5,
    borderRadius: 12,
    paddingVertical: 5,
    elevation: 6,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 6,
  },
  content: {
    paddingHorizontal: 20,
    paddingBottom: 120,
    paddingTop: 20,
  },

  sectionTitle: {
    color: "white",
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 12,
  },

  card: {
    borderRadius: 18,
    overflow: "hidden",
    marginBottom: 18,
    backgroundColor: "rgba(255,255,255,0.95)",
  },

  cardImage: { width: "100%", height: 145 },
  cardTitle: { fontSize: 18, fontWeight: "700", marginTop: 8 },
  cardSub: { color: "#555" },
  cardPrice: { marginTop: 6, fontWeight: "600", color: "#6C3BFF" },
animatedMenu: {
  overflow: "hidden",
  marginHorizontal: 15,
  marginTop: 5,
  borderRadius: 16,
},

glassMenu: {
  flex: 1,
  borderRadius: 16,
  paddingVertical: 8,
  backgroundColor: "rgba(120, 90, 255, 0.25)", // bluish purple tint
  borderWidth: 1,
  borderColor: "rgba(255,255,255,0.2)",
  overflow: "hidden",
},

menuItem: {
  flexDirection: "row",
  alignItems: "center",
  paddingVertical: 12,
  paddingHorizontal: 18,
},

menuItemText: {
  marginLeft: 12,
  fontSize: 16,
  fontWeight: "600",
  color: "white",
},
  fab: {
    position: "absolute",
    bottom: 35,
    right: 25,
    backgroundColor: "#6C3BFF",
    padding: 16,
    borderRadius: 40,
  },

  statusText: {
    color: "white",
    fontWeight: "700",
    fontSize: 12,
  },
});

// STATUS BADGE COLORS
const statusBadge = (published: boolean): ViewStyle => ({
  marginTop: 10,
  backgroundColor: published ? "#4CAF50" : "#FFA000",
  paddingVertical: 4,
  paddingHorizontal: 10,
  borderRadius: 12,
});