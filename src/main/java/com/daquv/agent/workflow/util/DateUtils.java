package com.daquv.agent.workflow.util;

import lombok.extern.slf4j.Slf4j;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

@Slf4j
public class DateUtils {

    /**
     * 현재 날짜와 시간을 반환
     */
    public static LocalDateTime getToday() {
        return LocalDateTime.now();
    }

    /**
     * 현재 날짜를 YYYYMMDD 형식의 문자열로 반환
     */
    public static String getTodayStr() {
        return getToday().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
    }

    /**
     * 현재 날짜를 'YYYY년 MM월 DD일' 형식의 문자열로 반환
     */
    public static String getTodayFormatted() {
        return getToday().format(DateTimeFormatter.ofPattern("yyyy년 MM월 dd일"));
    }

    /**
     * 현재 날짜를 'YYYY-MM-DD' 형식의 문자열로 반환
     */
    public static String getTodayDash() {
        return getToday().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
    }

    /**
     * 현재 요일을 한글 문자열로 반환
     */
    public static String getWeekday() {
        String[] weekdays = {"월", "화", "수", "목", "금", "토", "일"};
        return weekdays[getToday().getDayOfWeek().getValue() - 1];
    }

    /**
     * 현재 날짜와 요일을 'YYYYMMDD 요일요일' 형식으로 반환
     */
    public static String formatDateWithWeekday() {
        return getTodayStr() + " " + getWeekday() + "요일";
    }

    /**
     * 다양한 날짜 형식을 YYYYMMDD 형식으로 변환
     */
    public static String convertDateFormat(String dateStr) {
        if (dateStr == null) return dateStr;

        dateStr = dateStr.trim();

        if (dateStr.length() == 8 && dateStr.matches("\\d{8}")) {
            return dateStr;
        }
        else if (dateStr.length() == 10 && dateStr.charAt(4) == '-' && dateStr.charAt(7) == '-') {
            return dateStr.replace("-", "");
        }

        return dateStr;
    }

    /**
     * 날짜 문자열에 일수를 더하거나 뺌
     */
    public static String addDays(String dateStr, int days) {
        try {
            LocalDate date = LocalDate.parse(dateStr, DateTimeFormatter.ofPattern("yyyyMMdd"));
            LocalDate newDate = date.plusDays(days);
            return newDate.format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        } catch (Exception e) {
            log.error("Error adding days to date: {}", e.getMessage());
            return dateStr;
        }
    }

    /**
     * 날짜가 미래인지 확인
     */
    public static boolean isFutureDate(String dateStr) {
        try {
            return dateStr.compareTo(getTodayStr()) > 0;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 과거 데이터 접근 제한 체크
     */
    public static boolean checkPastDateAccess(String fromDate, int daysThreshold) {
        try {
            LocalDate fromDt = LocalDate.parse(fromDate, DateTimeFormatter.ofPattern("yyyyMMdd"));
            LocalDate today = LocalDate.now();
            long dateDiff = ChronoUnit.DAYS.between(fromDt, today);
            return dateDiff >= daysThreshold;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 과거 데이터 접근 제한 체크 (기본값: 2일)
     */
    public static boolean checkPastDateAccess(String fromDate) {
        return checkPastDateAccess(fromDate, 2);
    }
}
