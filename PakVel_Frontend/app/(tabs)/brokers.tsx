import { MaterialIcons } from "@expo/vector-icons";
import Slider from "@react-native-community/slider";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Image,
  ImageBackground,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";
import { api } from "../api/axiosInstance";

export default function BrokersScreen() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [itineraries, setItineraries] = useState<any[]>([]);

  // Filters
  const [city, setCity] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minRating, setMinRating] = useState(0);

  const [filterOpen, setFilterOpen] = useState(false);

  useEffect(() => {
    fetchItineraries();
  }, []);

  const fetchItineraries = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (city) params.city = city;
      if (minPrice) params.min_price = Number(minPrice);
      if (maxPrice) params.max_price = Number(maxPrice);
      if (minRating > 0) params.min_rating = minRating;

      const res = await api.get("/broker/public/itineraries", { params });
      setItineraries(res.data);
    } catch (err) {
      console.log("Fetch itineraries error:", err);
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setCity("");
    setMinPrice("");
    setMaxPrice("");
    setMinRating(0);
    fetchItineraries();
    setFilterOpen(false);
  };

  return (
    <ImageBackground
      source={require("../../assets/images/pattern.jpg")}
      style={{ flex: 1 }}
      resizeMode="cover"
      imageStyle={{ opacity: 0.99 }}
    >
      <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>
        
        {/* HEADER */}
        <LinearGradient
          colors={["#58C7FF", "#6C3BFF"]}
          style={styles.header}
        >
          <Text style={styles.headerTitle}>Broker Packages</Text>
        </LinearGradient>

        <ScrollView style={styles.container}>

          {/* SEARCH BAR */}
          <View style={styles.searchBox}>
            <TextInput
              placeholder="Search city"
              value={city}
              onChangeText={setCity}
              style={styles.searchInput}
            />
            <TouchableOpacity onPress={fetchItineraries}>
              <MaterialIcons name="search" size={26} color="#6C3BFF" />
            </TouchableOpacity>
          </View>

          {/* LIST */}
          {loading ? (
            <ActivityIndicator size="large" style={{ marginTop: 30 }} />
          ) : itineraries.length === 0 ? (
            <Text style={{ textAlign: "center", marginTop: 20 }}>
              No packages found
            </Text>
          ) : (
            itineraries.map((item) => (
              <TouchableOpacity
                key={item._id}
                style={styles.card}
                onPress={() =>
                  router.push({
                    pathname: "/user-brokerViewItinerary",
                    params: { id: item._id },
                  })
                }
              >
                <Image
                  source={
                    item.cover_image
                      ? { uri: item.cover_image }
                      : require("../../assets/images/sample-trip.png")
                  }
                  style={styles.image}
                />

                <View style={styles.cardContent}>
                  <Text style={styles.orgName}>
                                  {item.broker_org_name || "Independant Broker"}
                              </Text>
                  <Text style={styles.title}>{item.title}</Text>
                  <Text style={styles.subText}>
                    {(item.trip_locations || []).join(", ")}
                  </Text>
                  <Text style={styles.subText}>
                    ⭐ {item.avgRating} ({item.reviewCount} reviews)
                  </Text>
                  <Text style={styles.price}>
                    PKR {item.price_per_person}
                  </Text>
                </View>
              </TouchableOpacity>
            ))
          )}
        </ScrollView>

        {/* FLOATING FILTER BUTTON */}
        <TouchableOpacity style={styles.fab} onPress={() => setFilterOpen(true)}>
          <MaterialIcons name="tune" size={26} color="white" />
        </TouchableOpacity>

        {/* FILTER MODAL */}
        {filterOpen && (
          <View style={styles.overlay}>
            <View style={styles.modal}>
              <Text style={styles.modalTitle}>Filters</Text>

              <TextInput
                placeholder="Min Budget (PKR)"
                value={minPrice}
                onChangeText={setMinPrice}
                keyboardType="numeric"
                style={styles.input}
              />

              <TextInput
                placeholder="Max Budget (PKR)"
                value={maxPrice}
                onChangeText={setMaxPrice}
                keyboardType="numeric"
                style={styles.input}
              />

              <Text style={styles.sliderLabel}>
                Minimum Rating: ⭐ {minRating}
              </Text>

              <Slider
                minimumValue={0}
                maximumValue={5}
                step={1}
                value={minRating}
                onValueChange={setMinRating}
                minimumTrackTintColor="#6C3BFF"
                maximumTrackTintColor="#ccc"
              />

              <TouchableOpacity
                style={styles.applyBtn}
                onPress={() => {
                  setFilterOpen(false);
                  fetchItineraries();
                }}
              >
                <Text style={styles.applyText}>Apply Filters</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={clearFilters}>
                <Text style={styles.clearText}>Remove all filters</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </LinearGradient>
    </ImageBackground>
  );
}

/* ---------------- STYLES ---------------- */

const styles = StyleSheet.create({
  header: {
    paddingTop: 42,
    paddingBottom: 20,
    alignItems: "center",
    borderBottomLeftRadius: 18,
    borderBottomRightRadius: 18,
    elevation: 5,
  },
  headerTitle: {
    color: "white",
    fontSize: 24,
    fontWeight: "800",
  },
  container: { padding: 16 },

  searchBox: {
    flexDirection: "row",
    backgroundColor: "white",
    borderRadius: 12,
    paddingHorizontal: 12,
    alignItems: "center",
    marginBottom: 16,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 10,
  },

  card: {
    backgroundColor: "white",
    borderRadius: 14,
    marginBottom: 16,
    overflow: "hidden",
  },
  image: { width: "100%", height: 160 },
  cardContent: { padding: 12 },

  title: { fontSize: 18, fontWeight: "700" },
  subText: { fontSize: 14, color: "#666", marginTop: 4 },
  price: { marginTop: 8, fontSize: 16, fontWeight: "800", color: "#6C3BFF" },

  fab: {
    position: "absolute",
    right: 20,
    bottom: 30,
    backgroundColor: "#6C3BFF",
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: "center",
    alignItems: "center",
    elevation: 6,
  },

  overlay: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    alignItems: "center",
  },
  modal: {
    backgroundColor: "white",
    width: "85%",
    borderRadius: 16,
    padding: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 12,
  },
  input: {
    backgroundColor: "#f1f1f1",
    borderRadius: 10,
    padding: 10,
    marginBottom: 10,
  },
  sliderLabel: {
    marginTop: 10,
    fontWeight: "700",
  },
  applyBtn: {
    backgroundColor: "#6C3BFF",
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 14,
  },
  applyText: { color: "white", fontWeight: "700" },
  clearText: {
    marginTop: 10,
    textAlign: "center",
    color: "#666",
  },
  orgName: {
  fontSize: 14,
  fontWeight: "600",
  color: "#6B7280", // soft gray
  marginBottom: 4,
},
});