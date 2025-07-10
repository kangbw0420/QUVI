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
     * @return 현재 날짜와 시간
     */
    public static LocalDateTime getToday() {
        return LocalDateTime.now();
    }

    /**
     * 현재 날짜를 YYYYMMDD 형식의 문자열로 반환
     * @return YYYYMMDD 형식의 날짜 문자열
     */
    public static String getTodayStr() {
        return LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
    }

    /**
     * 현재 날짜를 'YYYY년 MM월 DD일' 형식의 문자열로 반환
     * @return YYYY년 MM월 DD일 형식의 날짜 문자열
     */
    public static String getTodayFormatted() {
        return LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy년 MM월 dd일"));
    }

    /**
     * 현재 날짜를 'YYYY-MM-DD' 형식의 문자열로 반환
     * @return YYYY-MM-DD 형식의 날짜 문자열
     */
    public static String getTodayDash() {
        return LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
    }

    /**
     * 현재 요일을 한글 문자열로 반환
     * @return 한글 요일 문자열
     */
    public static String getWeekday() {
        LocalDate today = LocalDate.now();
        return getWeekday(today.getDayOfWeek().getValue());
    }

    /**
     * 요일 번호를 한글 요일로 변환
     * @param dayOfWeek 요일 번호 (1=월요일, 7=일요일)
     * @return 한글 요일 문자열
     */
    public static String getWeekday(int dayOfWeek) {
        String[] weekdays = {"", "월", "화", "수", "목", "금", "토", "일"};
        return weekdays[dayOfWeek];
    }

    /**
     * 현재 날짜와 요일을 'YYYYMMDD 요일요일' 형식으로 반환
     * @return YYYYMMDD 요일요일 형식의 문자열
     */
    public static String formatDateWithWeekday() {
        return getTodayStr() + " " + getWeekday() + "요일";
    }

    /**
     * 질문에 날짜 정보를 추가하여 포맷팅
     * @param userQuestion 사용자 질문
     * @return 날짜 정보가 포함된 질문
     */
    public static String formatQuestionWithDate(String userQuestion) {
        return userQuestion + ", 오늘: " + formatDateWithWeekday() + ".";
    }

    /**
     * 다양한 날짜 형식을 YYYYMMDD 형식으로 변환
     * @param dateStr 변환할 날짜 문자열 (YYYYMMDD 또는 YYYY-MM-DD 형식)
     * @return YYYYMMDD 형식의 날짜 문자열
     */
    public static String convertDateFormat(String dateStr) {
        if (dateStr == null) {
            return null;
        }

        // 공백 제거
        dateStr = dateStr.trim();

        if (dateStr.length() == 8 && dateStr.matches("\\d{8}")) {
            return dateStr;
        }
        // YYYY-MM-DD 형식 검사 및 변환
        else if (dateStr.length() == 10 && dateStr.matches("\\d{4}-\\d{2}-\\d{2}")) {
            return dateStr.replace("-", "");
        }
        return dateStr;
    }

    /**
     * 날짜 문자열에 일수를 더하거나 뺌
     * @param dateStr YYYYMMDD 형식의 날짜 문자열
     * @param days 더하거나 뺄 일수 (음수면 빼기)
     * @return YYYYMMDD 형식의 날짜 문자열
     */
    public static String addDays(String dateStr, int days) {
        try {
            LocalDate dateObj = LocalDate.parse(dateStr, DateTimeFormatter.ofPattern("yyyyMMdd"));
            LocalDate newDate = dateObj.plusDays(days);
            return newDate.format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        } catch (Exception e) {
            System.err.println("Error adding days to date: " + e.getMessage());
            return dateStr;
        }
    }

    /**
     * 날짜가 미래인지 확인
     * @param dateStr YYYYMMDD 형식의 날짜 문자열
     * @return 미래 날짜면 true, 아니면 false
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
     * @param fromDate YYYYMMDD 형식의 시작 날짜
     * @param daysThreshold 과거 데이터 접근 제한 일수 (기본값: 2일)
     * @return 제한된 과거 데이터면 true, 아니면 false
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
     * @param fromDate YYYYMMDD 형식의 시작 날짜
     * @return 제한된 과거 데이터면 true, 아니면 false
     */
    public static boolean checkPastDateAccess(String fromDate) {
        return checkPastDateAccess(fromDate, 2);
    }

    /**
     * 현재 날짜와 시간을 'yyyy-MM-dd HH:mm:ss' 형식으로 반환
     * @return yyyy-MM-dd HH:mm:ss 형식의 날짜시간 문자열
     */
    public static String getCurrentDateTime() {
        return LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
    }

    /**
     * yyyy-MM-dd HH:mm:ss 형식의 DateTimeFormatter 반환
     * @return DateTimeFormatter
     */
    public static DateTimeFormatter getDateTimeFormatter() {
        return DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    }

    /**
     * yyyyMMdd 형식의 DateTimeFormatter 반환
     * @return DateTimeFormatter
     */
    public static DateTimeFormatter getDateFormatter() {
        return DateTimeFormatter.ofPattern("yyyyMMdd");
    }
}
