// /src/chat/cometchat.ts
import { CometChat } from "@cometchat/chat-sdk-react-native";

let isInitialized = false;

export const initCometChat = async () => {
  if (isInitialized) {
    console.log("ℹ️ CometChat already initialized");
    return;
  }

  const appID = "1674770a6701810ed"; // ✅ App ID
  const region = "in";              // ✅ Region

  const appSettings = new CometChat.AppSettingsBuilder()
    .setRegion(region)
    .subscribePresenceForAllUsers()
    .autoEstablishSocketConnection(true)
    .build();

  try {
    console.log("🟡 Initializing CometChat SDK...");
    await CometChat.init(appID, appSettings);
    isInitialized = true;
    console.log("🟢 CometChat initialized in AUTH TOKEN mode");
  } catch (error) {
    console.error("❌ CometChat init failed:", error);
    throw error;
  }
};