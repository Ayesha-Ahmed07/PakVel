import { MaterialCommunityIcons, MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
    Alert,
    Image,
    ImageBackground,
    ScrollView,
    StyleSheet,
    TouchableOpacity,
    View,
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";
import { api } from "./api/axiosInstance";

export default function BrokerViewItinerary() {
  const { id } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [itinerary, setItinerary] = useState<any>(null);

  useEffect(() => {
    loadDetails();
  }, []);

  const loadDetails = async () => {
    try {
      const res = await api.get(`/broker/itineraries/${id}`);
      setItinerary(res.data.itinerary);
    } catch (err) {
      console.log("Detail error:", err);
    } finally {
      setLoading(false);
    }
  };

  const deleteItinerary = async () => {
    Alert.alert(
      "Delete Itinerary",
      "Are you sure you want to delete this itinerary?",
      [
        { text: "Cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              const token = await AsyncStorage.getItem("token");
              await api.delete(`/broker/delete-itineraries/${id}`, {
                headers: { Authorization: `Bearer ${token}` },
              });
              router.replace("/brokerDashboard");
            } catch (err) {
              console.log("Delete error:", err);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Loading itinerary...</Text>
      </View>
    );
  }

  if (!itinerary) {
    return <Text style={{ padding: 20 }}>No data found</Text>;
  }

  return (
    <ImageBackground
      source={
        itinerary.cover_image
          ? { uri: itinerary.cover_image }
          : require("../assets/images/sample-trip.png")
      }
      style={{ flex: 1 }}
      resizeMode="cover"
      imageStyle={{ opacity: 0.25 }}
    >
      <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>
        
        {/* HEADER */}
        <LinearGradient colors={["#7F6CFF", "#A7D8FF"]} style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <MaterialIcons name="arrow-back" size={26} color="white" />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>Itinerary Details</Text>
        </LinearGradient>

        <ScrollView style={{ flex: 1 }}>

          {/* COVER IMAGE */}
          <Image
            source={
              itinerary.cover_image
                ? { uri: itinerary.cover_image }
                : require("../assets/images/sample-trip.png")
            }
            style={styles.image}
          />

          {/* MAIN INFO */}
          <View style={styles.mainBox}>
            <Text style={styles.title}>{itinerary.title}</Text>

            <View style={styles.row}>
              <MaterialIcons name="flight-takeoff" size={20} color="#6C3BFF" />
              <Text style={styles.subText}>
                Departure: {itinerary.departure_location}
              </Text>
            </View>

            <View style={styles.row}>
              <MaterialIcons name="flight-land" size={20} color="#6C3BFF" />
              <Text style={styles.subText}>
                Arrival: {itinerary.arrival_location}
              </Text>
            </View>

            <View style={[styles.row, { alignItems: "flex-start" }]}>
              <MaterialIcons name="map" size={20} color="#6C3BFF" />
              <View style={{ marginLeft: 6 }}>
                {itinerary.trip_locations?.map((loc: string, i: number) => (
                  <Text key={i} style={styles.subText}>• {loc}</Text>
                ))}
              </View>
            </View>

            <View style={styles.row}>
              <MaterialIcons name="calendar-today" size={20} color="#6C3BFF" />
              <Text style={styles.subText}>
                {itinerary.duration_days} days
              </Text>
            </View>

            <Text style={styles.price}>
              PKR {itinerary.price_per_person}
            </Text>
          </View>

          {/* DESCRIPTION */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Description</Text>
            <Text style={styles.sectionText}>{itinerary.description}</Text>
          </View>

          {/* DAY-BY-DAY PLAN — HORIZONTAL SLIDER */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Day-by-Day Plan</Text>

            <ScrollView
              horizontal={true}
              pagingEnabled={true}
              showsHorizontalScrollIndicator={false}
              style={{ marginVertical: 10 }}
            >
              {itinerary.days?.map((d: any, index: number) => (
                <View key={index} style={styles.dayCardHorizontal}>
                  <View style={styles.dayHeader}>
                    <MaterialIcons name="today" size={24} color="white" />
                    <Text style={styles.dayHeaderText}>Day {d.day_number}</Text>
                  </View>

                  <Text style={styles.dayText}>• Morning: {d.activities}</Text>
                  <Text style={styles.dayText}>• Afternoon: {d.meals_inc}</Text>
                  <Text style={styles.dayText}>• Evening: {d.hotel}</Text>
                </View>
              ))}
            </ScrollView>
          </View>

          {/* CONTACT INFO */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Contact Information</Text>

            <View style={styles.row}>
              <MaterialIcons name="phone" size={22} color="#6C3BFF" />
              <Text style={styles.sectionText}>
                {itinerary.contact_info?.phone || "N/A"}
              </Text>
            </View>

            <View style={styles.row}>
              <MaterialCommunityIcons name="whatsapp" size={22} color="#25D366" />
              <Text style={styles.sectionText}>
                {itinerary.contact_info?.whatsapp || "N/A"}
              </Text>
            </View>

            <View style={styles.row}>
              <MaterialIcons name="email" size={22} color="#6C3BFF" />
              <Text style={styles.sectionText}>
                {itinerary.contact_info?.email || "N/A"}
              </Text>
            </View>
          </View>

          <View style={{ height: 90 }} />

        </ScrollView>

        {/* ACTION BUTTONS */}
        <View style={styles.actionBar}>
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: "#6C3BFF" }]}
            onPress={() =>
              router.push({
                pathname: "/brokerEditItinerary",
                params: { id },
              })
            }
          >
            <Text style={styles.actionText}>Update</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: "#FF3B30" }]}
            onPress={deleteItinerary}
          >
            <Text style={styles.actionText}>Delete</Text>
          </TouchableOpacity>
        </View>

      </LinearGradient>
    </ImageBackground>
  );
}

/* ---------------- STYLES ---------------- */
const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },

  header: {
    paddingTop: 55,
    paddingBottom: 25,
    paddingHorizontal: 20,
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
    textAlign: "center",
  },

  image: {
    width: "100%",
    height: 230,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },

  mainBox: {
    padding: 20,
    backgroundColor: "white",
    marginTop: -25,
    marginHorizontal: 15,
    borderRadius: 15,
    elevation: 3,
  },

  title: { fontSize: 24, fontWeight: "700" },

  row: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
  },

  subText: {
    marginLeft: 6,
    fontSize: 15,
    color: "#555",
  },

  price: {
    marginTop: 12,
    fontSize: 20,
    fontWeight: "800",
    color: "#6C3BFF",
  },

  section: {
    marginTop: 25,
    paddingHorizontal: 20,
  },

  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 8,
  },

  sectionText: {
    fontSize: 15,
    color: "#444",
  },

  /* ORIGINAL CARD STYLE (kept untouched) */
  dayCard: {
    backgroundColor: "white",
    borderRadius: 12,
    marginVertical: 10,
    overflow: "hidden",
    elevation: 3,
  },

  /* NEW HORIZONTAL CARD STYLE */
  dayCardHorizontal: {
    backgroundColor: "white",
    borderRadius: 12,
    width: 300,
    marginRight: 15,
    overflow: "hidden",
    elevation: 3,
  },

  dayHeader: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#6C3BFF",
    padding: 12,
  },

  dayHeaderText: {
    color: "white",
    fontSize: 18,
    fontWeight: "700",
    marginLeft: 10,
  },

  dayText: {
    fontSize: 15,
    padding: 10,
    paddingBottom: 0,
    color: "#444",
  },

  actionBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 15,
    backgroundColor: "white",
    borderTopWidth: 1,
    borderColor: "#ddd",
  },

  actionBtn: {
    flex: 1,
    marginHorizontal: 10,
    padding: 14,
    borderRadius: 10,
  },

  actionText: {
    color: "white",
    fontSize: 17,
    textAlign: "center",
    fontWeight: "700",
  },
});