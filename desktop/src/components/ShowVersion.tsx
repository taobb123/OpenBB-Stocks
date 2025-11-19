import { useState, useEffect } from "react";

let cachedVersion: string | null = null;

const safeGetVersion = async (): Promise<string> => {
  if (cachedVersion !== null) return cachedVersion;
  
  try {
    // 检查是否在 Tauri 环境中
    if (typeof window === "undefined") {
      cachedVersion = "";
      return "";
    }
    
    // 动态导入以避免在导入时访问 invoke
    const { getVersion } = await import("@tauri-apps/api/app");
    cachedVersion = await getVersion();
    return cachedVersion;
  } catch (error) {
    // 静默处理错误，不显示版本号
    // 不输出错误日志，避免控制台噪音
    cachedVersion = "";
    return "";
  }
};

export default function ShowVersion() {
  const [version, setVersion] = useState<string>(cachedVersion ?? "");

  useEffect(() => {
    if (cachedVersion !== null) return;
    safeGetVersion().then(setVersion);
  }, []);

  if (!version) return null;

  return (
    <div className="body-xs-regular text-theme-secondary">
      v{version}
    </div>
  );
}