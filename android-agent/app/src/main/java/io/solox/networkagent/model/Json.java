package io.solox.networkagent.model;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class Json {
    private Json() {}

    public static String escape(String value) {
        if (value == null) {
            return "";
        }
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    public static String stringValue(String json, String key, String defaultValue) {
        Matcher matcher = Pattern.compile("\\\"" + Pattern.quote(key) + "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"").matcher(json);
        return matcher.find() ? matcher.group(1).replace("\\\"", "\"").replace("\\\\", "\\") : defaultValue;
    }

    public static int intValue(String json, String key, int defaultValue) {
        Matcher matcher = Pattern.compile("\\\"" + Pattern.quote(key) + "\\\"\\s*:\\s*(-?\\d+)").matcher(json);
        return matcher.find() ? Integer.parseInt(matcher.group(1)) : defaultValue;
    }

    public static double doubleValue(String json, String key, double defaultValue) {
        Matcher matcher = Pattern.compile("\\\"" + Pattern.quote(key) + "\\\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)").matcher(json);
        return matcher.find() ? Double.parseDouble(matcher.group(1)) : defaultValue;
    }

    public static boolean booleanValue(String json, String key, boolean defaultValue) {
        Matcher matcher = Pattern.compile("\\\"" + Pattern.quote(key) + "\\\"\\s*:\\s*(true|false)").matcher(json);
        return matcher.find() ? Boolean.parseBoolean(matcher.group(1)) : defaultValue;
    }
}
