//app/traveleractivetrips.tsx
export const unstable_settings = { ssr: false };

import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Alert,
  Image,
  ImageBackground,
  LayoutAnimation,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View
} from "react-native";
import { ActivityIndicator } from "react-native-paper";
import { api } from "./api/axiosInstance";
  

/* ---------------- CONFIG ---------------- */
const GOOGLE_MAPS_STATIC_KEY = "YOUR_GOOGLE_MAPS_KEY";

/* ---------------- TYPES ---------------- */
type Trip = {
  trip_id: string;
  destination: string;
  budget: number;
  status: string;
  start_date: string;
  traveler_completed?: boolean;
  broker_completed?: boolean;
  broker_id?: string;
  itinerary_source_id: string;
};

export default function ActiveTripScreen() {
  const [loading, setLoading] = useState(true);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [weather, setWeather] = useState<any>(null);
  const [forecast, setForecast] = useState<any[]>([]);
  const [showForecast, setShowForecast] = useState(false);
  const [weatherAlert, setWeatherAlert] = useState<string | null>(null);
  const router = useRouter();

  const isCompletionPending = trip?.status === "completion_pending";
  const isCompleted = trip?.status === "completed";
  const { id } = useLocalSearchParams();

  /* ---------------- LOAD ACTIVE TRIP ---------------- */
  useEffect(() => {
    const load = async () => {
      try {
        const token = await AsyncStorage.getItem("token");

        const tripRes = await api.get("/trips/active/current", {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!tripRes.data.hasActiveTrip) {
          setLoading(false);
          return;
        }

        const activeTrip = tripRes.data.trip;
        setTrip(activeTrip);

        const weatherRes = await api.get(
          `/weather/live?city=${activeTrip.destination}`
        );

        const w = weatherRes.data.data;
        setWeather(w);

        if (["Thunderstorm", "Snow", "Extreme"].includes(w.weather[0].main)) {
          setWeatherAlert(
            `⚠️ Weather Alert: ${w.weather[0].main} in ${activeTrip.destination}`
          );
        }
      } catch (err) {
        console.error("Active trip load failed", err);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const handleComplete = async () => {
  try {
    const token = await AsyncStorage.getItem("token");

    await api.patch(`/trips/${trip?.trip_id}/complete`, {}, {
      headers: { Authorization: `Bearer ${token}` },
    });

    Alert.alert("Completion recorded");

    // reload trip
    const tripRes = await api.get("/trips/active/current", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (tripRes.data.hasActiveTrip) {
      setTrip(tripRes.data.trip);
    }

  } catch (err) {
    console.error(err);
    Alert.alert("Failed to complete trip");
  }
};
  /* ---------------- FORECAST (LAZY) ---------------- */
  const toggleForecast = async () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);

    if (!showForecast && forecast.length === 0 && trip) {
      const res = await api.get(
        `/weather/forecast?city=${trip.destination}`
      );

      const daily = Object.values(
        res.data.forecast.list.reduce((acc: any, item: any) => {
          const date = new Date(item.dt * 1000).toDateString();
          if (!acc[date]) acc[date] = item;
          return acc;
        }, {})
      ).slice(0, 5);

      setForecast(daily);
    }

    setShowForecast(!showForecast);
  };

  /* ---------------- UI STATES ---------------- */
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
        <Text>Loading active trip…</Text>
      </View>
    );
  }

  if (!trip) {
    return (
      <View style={styles.center}>
        <Text>No active trip</Text>
      </View>
    );
  }

  return (
    <ImageBackground
      source={require("../assets/images/dashboard-bg.jpg")}
      style={{ flex: 1 }}
      resizeMode="cover"
    >
      {/* DARK OVERLAY */}
      <LinearGradient
        colors={["rgba(0,0,0,0.55)", "rgba(0,0,0,0.25)"]}
        style={{ flex: 1 }}
      >
        {/* HEADER */}
        <LinearGradient colors={["#58C7FF", "#6C3BFF"]} style={styles.header}>
            <TouchableOpacity
                      style={styles.headerBack}
                      onPress={() => router.replace("/dashboard")}
                    >
                      <MaterialIcons name="arrow-back" size={22} color="white" />
                    </TouchableOpacity>
                    <TouchableOpacity
  style={styles.chatIcon}
  onPress={() => router.push(`/chat/${trip?.trip_id}`)}
>
  <MaterialIcons name="chat" size={22} color="white" />
</TouchableOpacity>
          <Text style={styles.headerTitle}>Active Trip</Text>
        </LinearGradient>

        <ScrollView contentContainerStyle={styles.container}>
          {isCompletionPending && (
  <View style={styles.completeBanner}>
    <Text style={styles.completeBannerText}>
      🎉 Your trip has ended. Please confirm completion.
    </Text>
  </View>
)}
          {/* ALERT */}
          {weatherAlert && (
            <View style={styles.alertBanner}>
              <MaterialIcons name="warning" size={20} color="#fff" />
              <Text style={styles.alertText}>{weatherAlert}</Text>
            </View>
          )}

         <View style={styles.tripCard}>
  <Text style={styles.destination}>{trip.destination}</Text>

  <View style={styles.metaRow}>
    <Text style={styles.metaText}>💰 PKR {trip.budget}</Text>
    <Text style={styles.metaText}>
      📅 {new Date(trip.start_date).toDateString()}
    </Text>
  </View>

  <View style={styles.statusBadge}>
    <Text style={styles.statusText}>
  {trip.status.toUpperCase()}
</Text>
  </View>
</View>
        <View style={styles.weatherCard}>
  <View style={styles.weatherTop}>
    <Text style={{ fontWeight: "800" }}>Weather</Text>
    <Text style={styles.weatherTemp}>
      {Math.round(weather.main.temp)}°
    </Text>
  </View>

  <View style={styles.conditionChip}>
    <Text style={styles.conditionText}>
      {weather.weather[0].description.toUpperCase()}
    </Text>
  </View>

  <View style={styles.weatherGrid}>
    <Text style={styles.weatherItem}>🌬 Wind {weather.wind.speed} m/s</Text>
    <Text style={styles.weatherItem}>💧 Humidity {weather.main.humidity}%</Text>
    <Text style={styles.weatherItem}>👁 Visibility {weather.visibility / 1000} km</Text>
    <Text style={styles.weatherItem}>🤒 Feels like {Math.round(weather.main.feels_like)}°</Text>
  </View>

  <Text style={styles.muted}>Updated just now</Text>
</View>

          {/* FORECAST */}
          <View style={styles.forecastCard}>
            <TouchableOpacity
              onPress={toggleForecast}
              style={styles.forecastHeader}
            >
              <Text style={styles.forecastHeader}>5-Day Forecast</Text>
              <MaterialIcons
                name={showForecast ? "expand-less" : "expand-more"}
                size={24}
              />
            </TouchableOpacity>

            {showForecast && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {forecast.map((f, idx) => (
                  <View key={idx} style={styles.forecastItem}>
                    <Text style={styles.forecastDay}>
                      {new Date(f.dt * 1000).toDateString().slice(0, 10)}
                    </Text>
                    <Text>🌡 {Math.round(f.main.temp)}°C</Text>
                    <Text>🤒 {Math.round(f.main.feels_like)}°C</Text>
                    <Text>💧 {f.main.humidity}%</Text>
                    <Text>📈 {f.main.pressure} hPa</Text>
                    <Text>{f.weather[0].main}</Text>
                  </View>
                ))}
              </ScrollView>
            )}
          </View>

          {/* STATIC MAP */}
          <View style={styles.mapCard}>
            <Image
              source={{
                uri: `https://maps.googleapis.com/maps/api/staticmap?center=${encodeURIComponent(
                  trip.destination
                )}&zoom=10&size=600x300&markers=color:red|${encodeURIComponent(
                  trip.destination
                )}&key=${GOOGLE_MAPS_STATIC_KEY}`,
              }}
              style={styles.map}
            />
          </View>

          {/* CTA */}
         {isCompletionPending ? (
  <TouchableOpacity
    activeOpacity={0.9}
    onPress={handleComplete}
    disabled={trip?.traveler_completed}
  >
    <LinearGradient
      colors={["#F59E0B", "#F97316"]}
      style={styles.routesBtn}
    >
      <MaterialIcons name="check-circle" size={22} color="#fff" />
      <Text style={styles.routesText}>
        {trip?.traveler_completed
          ? "Waiting for broker..."
          : "Complete Trip"}
      </Text>
    </LinearGradient>
  </TouchableOpacity>
) : (
  <TouchableOpacity activeOpacity={0.9}>
    <LinearGradient
      colors={["#2563EB", "#4F46E5"]}
      style={styles.routesBtn}
    >
      <MaterialIcons name="map" size={22} color="#fff" />
      <Text style={styles.routesText}>View Routes</Text>
    </LinearGradient>
  </TouchableOpacity>
)}

        </ScrollView>
      </LinearGradient>
    </ImageBackground>
  );
}

/* ---------------- STYLES ---------------- */
/* ---------------- STYLES ---------------- */

const GLASS = "rgba(255,255,255,0.88)";

const styles = StyleSheet.create({
  header: {
    paddingTop: 42,
    paddingBottom: 18,
    alignItems: "center",
    borderBottomLeftRadius: 26,
    borderBottomRightRadius: 26,
    elevation: 10,
  },

  headerTitle: {
    color: "#fff",
    fontSize: 23,
    fontWeight: "900",
    letterSpacing: 0.5,
  },

  container: {
    padding: 16,
    paddingBottom: 60,
  },

  
completeBanner: {
  backgroundColor: "#f5780bff",
  padding: 12,
  borderRadius: 16,
  marginBottom: 12,
},

completeBannerText: {
  color: "white",
  fontWeight: "800",
  textAlign: "center",
},

chatIcon: {
  position: "absolute",
  right: 16,
  bottom: 16,
},
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  headerBack: {
    position: "absolute",
    left: 16,
    bottom: 16,
    padding: 3,
    
  },

  /* 🌟 HERO TRIP CARD */
  tripCard: {
    backgroundColor: GLASS,
    borderRadius: 22,
    padding: 18,
    marginBottom: 18,
    elevation: 10,
    shadowOpacity: 0.15,
    shadowRadius: 14,
  },

  destination: {
    fontSize: 22,
    fontWeight: "900",
    color: "#111827",
  },

  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
    gap: 10,
  },

  metaText: {
    color: "#374151",
    fontSize: 13,
  },

  statusBadge: {
    marginTop: 12,
    backgroundColor: "#22C55E",
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 999,
    alignSelf: "flex-start",
  },

  statusText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 12,
    letterSpacing: 0.5,
  },

  /* 🌤 WEATHER CARD */
  weatherCard: {
    backgroundColor: "rgba(255,255,255,0.92)",
    borderRadius: 22,
    padding: 18,
    marginBottom: 18,
    elevation: 10,
  },

  weatherTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  weatherTemp: {
    fontSize: 34,
    fontWeight: "900",
    color: "#2563EB",
  },

  conditionChip: {
    backgroundColor: "#EEF2FF",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    marginTop: 8,
    alignSelf: "flex-start",
  },

  conditionText: {
    color: "#3730A3",
    fontWeight: "700",
    fontSize: 13,
  },

  weatherGrid: {
    marginTop: 14,
    gap: 6,
  },

  weatherItem: {
    fontSize: 13,
    color: "#374151",
  },

  muted: {
    fontSize: 11,
    color: "#6B7280",
    marginTop: 10,
  },

  /* 🔮 FORECAST */
  forecastCard: {
    backgroundColor: GLASS,
    borderRadius: 22,
    padding: 18,
    marginBottom: 18,
  },

  forecastHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  forecastItem: {
    width: 150,
    marginRight: 14,
    marginTop: 14,
    padding: 14,
    borderRadius: 18,
    backgroundColor: "#F8FAFF",
    elevation: 4,
  },

  forecastDay: {
    fontWeight: "800",
    marginBottom: 6,
    color: "#111827",
  },

  /* 🗺 MAP */
  mapCard: {
    backgroundColor: GLASS,
    borderRadius: 22,
    padding: 12,
    marginBottom: 22,
  },

  mapTitle: {
    fontWeight: "800",
    marginBottom: 8,
    color: "#111827",
  },

  map: {
    width: "100%",
    height: 180,
    borderRadius: 18,
  },

  /* 🚀 CTA */
  routesBtn: {
    borderRadius: 22,
    paddingVertical: 16,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    elevation: 12,
    bottom:15,
  },

  routesText: {
    color: "#fff",
    fontWeight: "900",
    fontSize: 17,
    marginLeft: 8,
  },

  /* 🚨 ALERT */
  alertBanner: {
    backgroundColor: "#DC2626",
    padding: 14,
    borderRadius: 18,
    marginBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },

  alertText: {
    color: "#fff",
    fontWeight: "800",
  },

  modal: {
    backgroundColor: "white",
    width: "85%",
    borderRadius: 14,
    padding: 16,
  },

  modalTitle: {
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 10,
  },

  reviewInput: {
    backgroundColor: "#f1f1f1",
    borderRadius: 8,
    padding: 10,
    marginTop: 10,
    height: 80,
  },

  submitBtn: {
    backgroundColor: "#6C3BFF",
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 12,
  },

  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    alignItems: "center",
  },
});