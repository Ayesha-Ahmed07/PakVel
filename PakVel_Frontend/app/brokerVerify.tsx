import { Picker } from "@react-native-picker/picker";
import { router, useLocalSearchParams } from "expo-router";
import React, { useState } from "react";
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import api from "./api/axiosInstance";

const SPECIALIZATION_OPTIONS = [
  "Adventure and Nature Tourism",
  "Northern Areas Specialist",
  "Luxury Travel",
  "Cultural Travel",
  "Religious Tourism",
  "Honeymoon Packages",
  "Corporate Travel Management",
  "Family Vacation Planning",
  "International Tours",
];

export default function BrokerVerify() {
  const { email } = useLocalSearchParams();

  const [orgName, setOrgName] = useState("");
  const [phone, setPhone] = useState("");
  const [cnic, setCnic] = useState("");
  const [license, setLicense] = useState("");

  const [tagline, setTagline] = useState("");
  const [years, setYears] = useState<number>(1);
  const [specializations, setSpecializations] = useState<string[]>([]);

  const toggleSpecialization = (area: string) => {
    if (specializations.includes(area)) {
      setSpecializations(specializations.filter((a) => a !== area));
    } else {
      setSpecializations([...specializations, area]);
    }
  };

  const handleVerify = async () => {
    if (
      !orgName ||
      !phone ||
      !cnic ||
      !license ||
      !tagline ||
      !years ||
      specializations.length === 0
    ) {
      Alert.alert("Error", "All fields are required");
      return;
    }

    try {
      await api.post("/broker/verify", {
        email,
        org_name: orgName,
        phone,
        cnic,
        license_number: license,
        tagline,
        years_of_experience: years,
        specialized_areas: specializations,
      });

      Alert.alert("Success", "Verification submitted.");
      router.replace("/login");
    } catch (err: any) {
      Alert.alert(
        "Error",
        err.response?.data?.detail || "Verification failed."
      );
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.header}>Broker Verification</Text>

      {/* Organization */}
      <Text style={styles.label}>Organization Name</Text>
      <TextInput
        style={styles.input}
        onChangeText={setOrgName}
      />

      {/* Tagline */}
      <Text style={styles.label}>Tagline</Text>
      <TextInput
        placeholder="e.g. Your trusted travel partner"
        style={styles.input}
        onChangeText={setTagline}
      />

      {/* Experience Dropdown */}
      <Text style={styles.label}>Years of Experience</Text>
      <View style={styles.pickerContainer}>
        <Picker
          selectedValue={years}
          onValueChange={(itemValue) => setYears(itemValue)}
        >
          {[...Array(31).keys()].slice(1).map((num) => (
            <Picker.Item
              key={num}
              label={`${num} Years`}
              value={num}
            />
          ))}
        </Picker>
      </View>

      {/* Specializations */}
      <Text style={styles.label}>Specialized Areas</Text>
      <View style={styles.specializationContainer}>
        {SPECIALIZATION_OPTIONS.map((area) => {
          const selected = specializations.includes(area);
          return (
            <TouchableOpacity
              key={area}
              style={[
                styles.pill,
                selected && styles.pillSelected,
              ]}
              onPress={() => toggleSpecialization(area)}
            >
              <Text
                style={[
                  styles.pillText,
                  selected && styles.pillTextSelected,
                ]}
              >
                {area}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Phone */}
      <Text style={styles.label}>Phone Number</Text>
      <TextInput style={styles.input} onChangeText={setPhone} />

      {/* CNIC */}
      <Text style={styles.label}>CNIC</Text>
      <TextInput style={styles.input} onChangeText={setCnic} />

      {/* License */}
      <Text style={styles.label}>License Number</Text>
      <TextInput style={styles.input} onChangeText={setLicense} />

      <TouchableOpacity style={styles.mainBtn} onPress={handleVerify}>
        <Text style={styles.mainBtnTxt}>Submit Verification</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

/* -------------------- Styles -------------------- */

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingBottom: 40,
  },

  header: {
    fontSize: 26,
    fontWeight: "800",
    textAlign: "center",
    marginBottom: 25,
  },

  label: {
    marginTop: 14,
    marginBottom: 6,
    fontSize: 15,
    fontWeight: "600",
  },

  input: {
    borderWidth: 1,
    borderColor: "#ccc",
    padding: 12,
    borderRadius: 8,
  },

  pickerContainer: {
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
  },

  specializationContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },

  pill: {
    borderWidth: 1,
    borderColor: "#6C3BFF",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginBottom: 8,
  },

  pillSelected: {
    backgroundColor: "#6C3BFF",
  },

  pillText: {
    fontSize: 13,
  },

  pillTextSelected: {
    color: "white",
  },

  mainBtn: {
    backgroundColor: "#6C3BFF",
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 30,
  },

  mainBtnTxt: {
    textAlign: "center",
    color: "white",
    fontSize: 17,
    fontWeight: "700",
  },
});