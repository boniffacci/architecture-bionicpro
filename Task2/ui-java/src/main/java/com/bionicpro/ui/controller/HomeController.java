package com.bionicpro.ui.controller;

import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * Контроллер главной страницы и логина
 */
@Controller
public class HomeController {

    @GetMapping("/")
    public String home(Authentication authentication, Model model) {
        if (authentication != null && authentication.isAuthenticated()) {
            model.addAttribute("authenticated", true);
            
            if (authentication instanceof OAuth2AuthenticationToken oauth2Token) {
                OAuth2User user = oauth2Token.getPrincipal();
                model.addAttribute("username", user.getAttribute("preferred_username"));
                model.addAttribute("email", user.getAttribute("email"));
            }
            
            return "redirect:/reports";
        }
        
        return "index";
    }

    @GetMapping("/login")
    public String login() {
        return "login";
    }

}


