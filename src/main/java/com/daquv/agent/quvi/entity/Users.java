package com.daquv.agent.quvi.entity;

import javax.persistence.*;

@Entity
@Table(name = "users", schema = "public")
public class Users {

    @Id
    @Column(name = "user_id", length = 100, nullable = false)
    private String userId;

    @Column(name = "user_pwd", length = 100, nullable = false)
    private String userPwd;

    @Column(name = "user_nm", length = 100, nullable = false)
    private String userNm;

    @Column(name = "role", length = 20, nullable = false)
    private String role = "customer";

    @Column(name = "company_id", length = 50)
    private String companyId;

    // 기본 생성자
    public Users() {}

    // 생성자 (필수 필드)
    public Users(String userId, String userPwd, String userNm) {
        this.userId = userId;
        this.userPwd = userPwd;
        this.userNm = userNm;
        this.role = "customer";
    }

    // 전체 필드 생성자
    public Users(String userId, String userPwd, String userNm, String role, String companyId) {
        this.userId = userId;
        this.userPwd = userPwd;
        this.userNm = userNm;
        this.role = role != null ? role : "customer";
        this.companyId = companyId;
    }

    // Getter 메서드들
    public String getUserId() {
        return userId;
    }

    public String getUserPwd() {
        return userPwd;
    }

    public String getUserNm() {
        return userNm;
    }

    public String getRole() {
        return role;
    }

    public String getCompanyId() {
        return companyId;
    }

    // Setter 메서드들
    public void setUserId(String userId) {
        this.userId = userId;
    }

    public void setUserPwd(String userPwd) {
        this.userPwd = userPwd;
    }

    public void setUserNm(String userNm) {
        this.userNm = userNm;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public void setCompanyId(String companyId) {
        this.companyId = companyId;
    }

    // toString 메서드
    @Override
    public String toString() {
        return "Users{" +
                "userId='" + userId + '\'' +
                ", userNm='" + userNm + '\'' +
                ", role='" + role + '\'' +
                ", companyId='" + companyId + '\'' +
                '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Users users = (Users) o;
        return userId != null ? userId.equals(users.userId) : users.userId == null;
    }

    @Override
    public int hashCode() {
        return userId != null ? userId.hashCode() : 0;
    }
}