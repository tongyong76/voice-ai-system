#include "device_config.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include "esp_mac.h"
#include <string.h>

static const char *TAG = "DEVICE_CONFIG";

#define NVS_NAMESPACE "device"
#define KEY_DEVICE_CODE "code"
#define KEY_SERVER_URL "server"
#define KEY_WIFI_SSID "ssid"
#define KEY_WIFI_PASS "pass"

static char s_device_code[32] = "";
static char s_server_url[128] = "http://192.168.1.100:8000";
static char s_wifi_ssid[64] = "";
static char s_wifi_password[64] = "";

static void generate_default_device_code(void)
{
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    snprintf(s_device_code, sizeof(s_device_code),
             "ESP32_%02X%02X%02X", mac[3], mac[4], mac[5]);
}

esp_err_t device_config_init(void)
{
    ESP_LOGI(TAG, "Loading device configuration from NVS");

    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs_handle);

    if (err != ESP_OK) {
        ESP_LOGW(TAG, "NVS open failed, using defaults");
        generate_default_device_code();
        return ESP_OK;
    }

    // Read device code
    size_t len = sizeof(s_device_code);
    err = nvs_get_str(nvs_handle, KEY_DEVICE_CODE, s_device_code, &len);
    if (err != ESP_OK) {
        generate_default_device_code();
    }

    // Read server URL
    len = sizeof(s_server_url);
    err = nvs_get_str(nvs_handle, KEY_SERVER_URL, s_server_url, &len);
    if (err != ESP_OK) {
        strcpy(s_server_url, "http://192.168.1.100:8000");
    }

    // Read Wi-Fi SSID
    len = sizeof(s_wifi_ssid);
    nvs_get_str(nvs_handle, KEY_WIFI_SSID, s_wifi_ssid, &len);

    // Read Wi-Fi password
    len = sizeof(s_wifi_password);
    nvs_get_str(nvs_handle, KEY_WIFI_PASS, s_wifi_password, &len);

    nvs_close(nvs_handle);

    ESP_LOGI(TAG, "Device code: %s", s_device_code);
    ESP_LOGI(TAG, "Server URL: %s", s_server_url);
    ESP_LOGI(TAG, "Wi-Fi SSID: %s", s_wifi_ssid[0] ? s_wifi_ssid : "(not set)");

    return ESP_OK;
}

const char *device_config_get_code(void)
{
    return s_device_code;
}

const char *device_config_get_server_url(void)
{
    return s_server_url;
}

const char *device_config_get_wifi_ssid(void)
{
    return s_wifi_ssid;
}

const char *device_config_get_wifi_password(void)
{
    return s_wifi_password;
}

esp_err_t device_config_set(
    const char *device_code,
    const char *server_url,
    const char *wifi_ssid,
    const char *wifi_password)
{
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        return err;
    }

    if (device_code) {
        strncpy(s_device_code, device_code, sizeof(s_device_code) - 1);
        nvs_set_str(nvs_handle, KEY_DEVICE_CODE, s_device_code);
    }

    if (server_url) {
        strncpy(s_server_url, server_url, sizeof(s_server_url) - 1);
        nvs_set_str(nvs_handle, KEY_SERVER_URL, s_server_url);
    }

    if (wifi_ssid) {
        strncpy(s_wifi_ssid, wifi_ssid, sizeof(s_wifi_ssid) - 1);
        nvs_set_str(nvs_handle, KEY_WIFI_SSID, s_wifi_ssid);
    }

    if (wifi_password) {
        strncpy(s_wifi_password, wifi_password, sizeof(s_wifi_password) - 1);
        nvs_set_str(nvs_handle, KEY_WIFI_PASS, s_wifi_password);
    }

    nvs_commit(nvs_handle);
    nvs_close(nvs_handle);

    ESP_LOGI(TAG, "Configuration saved");
    return ESP_OK;
}
