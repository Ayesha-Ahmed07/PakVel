export const unstable_settings = { ssr: false };

import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
    Alert,
    ImageBackground,
    Linking,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";
import { ActivityIndicator, Card } from "react-native-paper";
import { api } from "./api/axiosInstance";

/* ---------------- TYPES ---------------- */

type Trip = {
  trip_id: string;
  destination: string;
  budget: number;
  status: string;
  itinerary_source_id: string;
};

export default function SelfBookScreen() {
  //const { tripId } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [trip, setTrip] = useState<any>(null);
  const [itinerary, setItinerary] = useState<any>(null);
  const {tripId, itineraryId} = useLocalSearchParams();

  /* ---------------- LOAD TRIP + ITINERARY ---------------- */

  useEffect(() => {
    const load = async () => {
      try {
        const token = await AsyncStorage.getItem("token");

        // 1️⃣ Fetch Trip
        const tripRes = await api.get(`/trips/${tripId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        setTrip(tripRes.data);

        // 2️⃣ Fetch Attached Itinerary
        const itineraryRes = await api.get(
          `/traveler/itinerary/${tripRes.data.itinerary_source_id}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        setItinerary(itineraryRes.data);
      } catch (err) {
        console.log("SelfBook load error:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  /* ---------------- ACTIONS ---------------- */

  const openBooking = () => {
    const bookingUrl = `https://www.booking.com/searchresults.html?ss=${encodeURIComponent(
      itinerary.destination
    )}`;
    Linking.openURL(bookingUrl);
  };

  const [confirming, setConfirming] = useState(false);

const confirmTrip = async () => {
  try {
    setConfirming(true);

    const token = await AsyncStorage.getItem("token");

    await api.patch(
      `/trips/${tripId}/activate`,
      {},
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    // Navigate to Active Trips screen
    router.replace("/traveleractivetrips");

  } catch (err: any) {
    console.log("Activate trip error:", err);
    Alert.alert(
      "Error",
      err.response?.data?.detail || "Unable to activate trip."
    );
  } finally {
    setConfirming(false);
  }
};

  /* ---------------- UI STATES ---------------- */

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
        <Text>Preparing your booking...</Text>
      </View>
    );
  }

  if (!trip || !itinerary) {
    return (
      <View style={styles.center}>
        <Text>Something went wrong.</Text>
      </View>
    );
  }

  /* ---------------- UI ---------------- */

  return (
    <ImageBackground
      source={require("../assets/images/dashboard-bg.jpg")}
      style={{ flex: 1 }}
      resizeMode="cover"
      imageStyle={{ opacity: 0.95 }}
    >
      <LinearGradient
        colors={["rgba(0,0,0,0.35)", "rgba(0,0,0,0.6)"]}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.container}>

          {/* HEADER */}
<View style={styles.headerContainer}>

  <TouchableOpacity
    onPress={() =>
      router.replace(`/itinerary/${itineraryId}`)
    }
    style={styles.headerBack}
  >
    <MaterialIcons name="arrow-back" size={24} color="white" />
  </TouchableOpacity>

  <Text style={styles.headerTitle}>
    Self Booking
  </Text>

  {/* Spacer to balance header */}
  <View style={{ width: 24 }} />

</View>

          {/* TRIP SUMMARY */}
          <Card style={styles.card}>
            <Text style={styles.destination}>
              {itinerary.destination}
            </Text>

            <Text style={styles.meta}>
              🗓 {itinerary.duration} Days
            </Text>

            <Text style={styles.meta}>
              💰 Budget: PKR {itinerary.budget}
            </Text>

            <Text style={styles.meta}>
              ✨ AI Generated Plan
            </Text>
          </Card>

          {/* BOOKING SECTION */}
          <Card style={styles.card}>
            <Text style={styles.sectionTitle}>
              Book Hotels
            </Text>

            <Text style={styles.subText}>
              Find best hotel deals for {itinerary.destination}
            </Text>

            <TouchableOpacity
              style={styles.bookingBtn}
              onPress={openBooking}
            >
              <MaterialIcons name="hotel" size={22} color="white" />
              <Text style={styles.bookingText}>
                Search Hotels on Booking.com
              </Text>
            </TouchableOpacity>
          </Card>

          {/* CONFIRM CTA */}
          <TouchableOpacity
  style={[
    styles.confirmBtn,
    confirming && { opacity: 0.7 }
  ]}
  onPress={confirmTrip}
  disabled={confirming}
>
  {confirming ? (
    <ActivityIndicator color="white" />
  ) : (
    <>
      <MaterialIcons name="check-circle" size={22} color="white" />
      <Text style={styles.confirmText}>
        Confirm Trip
      </Text>
    </>
  )}
</TouchableOpacity>

        </ScrollView>
      </LinearGradient>
    </ImageBackground>
  );
}

/* ---------------- STYLES ---------------- */

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

  headerTitle: {
    color: "#fff",
    fontSize: 23,
    fontWeight: "900",
    letterSpacing: 0.5,
  },
headerBack: {
    position: "absolute",
    left: 16,
    bottom: 16,
    padding: 3,
    
  },
  headerContainer: {
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: 30,
},
  card: {
    backgroundColor: "rgba(255,255,255,0.9)",
    borderRadius: 20,
    padding: 20,
    marginBottom: 20,
  },

  destination: {
    fontSize: 22,
    fontWeight: "800",
    marginBottom: 10,
  },

  meta: {
    fontSize: 15,
    marginBottom: 6,
    color: "#444",
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 10,
  },

  subText: {
    fontSize: 14,
    color: "#555",
    marginBottom: 15,
  },

  bookingBtn: {
    backgroundColor: "#2563EB",
    paddingVertical: 14,
    borderRadius: 14,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  bookingText: {
    color: "white",
    fontWeight: "700",
    marginLeft: 8,
  },

  confirmBtn: {
    marginTop: 20,
    backgroundColor: "#16A34A",
    paddingVertical: 16,
    borderRadius: 18,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  confirmText: {
    color: "white",
    fontSize: 16,
    fontWeight: "800",
    marginLeft: 8,
  },
});