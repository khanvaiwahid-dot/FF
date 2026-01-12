"""
Garena Free Fire Top-Up Automation Module
Uses Playwright with stealth for browser automation
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

# Garena URLs
GARENA_LOGIN_URL = "https://sso.garena.com/universal/login"
GARENA_TOPUP_URL = "https://shop.garena.com/app/100067/id498"  # Free Fire BD
GARENA_TOPUP_URL_ALT = "https://shop2.garena.my/app/100067"    # Alternative

# Automation timeouts (ms)
DEFAULT_TIMEOUT = 30000
NAVIGATION_TIMEOUT = 60000


class GarenaAutomation:
    """
    Handles Garena Free Fire diamond top-up automation using Playwright.
    Includes anti-detection measures via playwright-stealth.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """Initialize browser with stealth settings"""
        self.playwright = await async_playwright().start()
        
        # Launch browser with anti-detection settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
            ]
        )
        
        # Create context with realistic settings
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Asia/Dhaka',
        )
        
        self.page = await context.new_page()
        
        # Apply stealth settings using Stealth class
        stealth = Stealth()
        await stealth.apply_stealth_async(self.page)
        
        # Set default timeouts
        self.page.set_default_timeout(DEFAULT_TIMEOUT)
        self.page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
        
        logger.info("Browser initialized with stealth settings")
        
    async def close(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
        
    async def login(self, email: str, password: str) -> bool:
        """
        Login to Garena account
        Returns True if login successful, False otherwise
        """
        try:
            logger.info(f"Attempting Garena login for: {email[:5]}***")
            
            # Navigate to login page
            await self.page.goto(GARENA_LOGIN_URL, wait_until='networkidle')
            await asyncio.sleep(2)  # Wait for any dynamic content
            
            # Wait for login form
            await self.page.wait_for_selector('input[type="text"], input[name="username"], input[placeholder*="email"], input[placeholder*="Email"]', timeout=10000)
            
            # Fill email/username
            email_input = await self.page.query_selector('input[type="text"], input[name="username"], input[placeholder*="email"], input[placeholder*="Email"]')
            if email_input:
                await email_input.fill(email)
                logger.info("Email entered")
            else:
                logger.error("Email input not found")
                return False
            
            # Fill password
            password_input = await self.page.query_selector('input[type="password"]')
            if password_input:
                await password_input.fill(password)
                logger.info("Password entered")
            else:
                logger.error("Password input not found")
                return False
            
            # Click login button
            login_btn = await self.page.query_selector('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")')
            if login_btn:
                await login_btn.click()
                logger.info("Login button clicked")
            else:
                # Try pressing Enter
                await password_input.press('Enter')
            
            # Wait for navigation or error
            await asyncio.sleep(3)
            
            # Check if login was successful (not on login page anymore)
            current_url = self.page.url
            if 'login' not in current_url.lower() or 'sso.garena.com' not in current_url:
                logger.info("Login successful")
                return True
            
            # Check for error messages
            error_msg = await self.page.query_selector('.error, .alert-danger, [class*="error"]')
            if error_msg:
                error_text = await error_msg.inner_text()
                logger.error(f"Login error: {error_text}")
                return False
            
            logger.warning("Login status unclear - checking for 2FA or captcha")
            return False
            
        except PlaywrightTimeout:
            logger.error("Login timeout")
            return False
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    async def navigate_to_topup(self, server_region: str = "BD") -> bool:
        """Navigate to Free Fire top-up page for specified region"""
        try:
            topup_url = GARENA_TOPUP_URL if server_region == "BD" else GARENA_TOPUP_URL_ALT
            
            logger.info(f"Navigating to top-up page: {topup_url}")
            await self.page.goto(topup_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Check if page loaded correctly
            title = await self.page.title()
            logger.info(f"Page title: {title}")
            
            return True
            
        except PlaywrightTimeout:
            logger.error("Navigation to top-up page timed out")
            return False
        except Exception as e:
            logger.error(f"Navigation error: {str(e)}")
            return False
    
    async def enter_player_uid(self, player_uid: str) -> bool:
        """Enter player UID for top-up"""
        try:
            logger.info(f"Entering player UID: {player_uid}")
            
            # Wait for UID input field
            uid_input = await self.page.wait_for_selector(
                'input[placeholder*="UID"], input[placeholder*="ID"], input[name*="uid"], input[name*="player"]',
                timeout=10000
            )
            
            if uid_input:
                await uid_input.fill(player_uid)
                logger.info("Player UID entered")
                
                # Click verify/check button if present
                verify_btn = await self.page.query_selector('button:has-text("Verify"), button:has-text("Check"), button:has-text("Confirm")')
                if verify_btn:
                    await verify_btn.click()
                    await asyncio.sleep(2)
                
                return True
            else:
                logger.error("UID input not found")
                return False
                
        except PlaywrightTimeout:
            logger.error("UID input timeout")
            return False
        except Exception as e:
            logger.error(f"UID entry error: {str(e)}")
            return False
    
    async def validate_player(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that the player UID exists and get player name
        Returns (success, player_name)
        """
        try:
            await asyncio.sleep(2)
            
            # Look for player name display
            player_name_elem = await self.page.query_selector('[class*="player-name"], [class*="username"], .user-info')
            if player_name_elem:
                player_name = await player_name_elem.inner_text()
                logger.info(f"Player validated: {player_name}")
                return True, player_name.strip()
            
            # Check for error messages
            error_elem = await self.page.query_selector('.error, .alert-danger, [class*="invalid"]')
            if error_elem:
                error_text = await error_elem.inner_text()
                logger.error(f"Player validation failed: {error_text}")
                return False, None
            
            # Assume validation passed if no error
            return True, None
            
        except Exception as e:
            logger.error(f"Player validation error: {str(e)}")
            return False, None
    
    async def select_package(self, diamond_amount: int) -> bool:
        """Select the diamond package to purchase"""
        try:
            logger.info(f"Selecting package: {diamond_amount} diamonds")
            
            # Try various selectors for package selection
            selectors = [
                f'[data-diamonds="{diamond_amount}"]',
                f'button:has-text("{diamond_amount}")',
                f'.package:has-text("{diamond_amount}")',
                f'.item:has-text("{diamond_amount}")',
            ]
            
            for selector in selectors:
                package = await self.page.query_selector(selector)
                if package:
                    await package.click()
                    logger.info(f"Package selected using selector: {selector}")
                    await asyncio.sleep(1)
                    return True
            
            logger.error(f"Package with {diamond_amount} diamonds not found")
            return False
            
        except Exception as e:
            logger.error(f"Package selection error: {str(e)}")
            return False
    
    async def complete_purchase(self, garena_pin: Optional[str] = None) -> bool:
        """
        Complete the purchase process
        May require PIN for shell balance purchases
        """
        try:
            logger.info("Completing purchase...")
            
            # Click purchase/buy button
            buy_btn = await self.page.query_selector(
                'button:has-text("Buy"), button:has-text("Purchase"), button:has-text("Confirm"), button[type="submit"]'
            )
            
            if buy_btn:
                await buy_btn.click()
                logger.info("Buy button clicked")
                await asyncio.sleep(3)
            
            # Check for PIN prompt
            pin_input = await self.page.query_selector('input[type="password"][placeholder*="PIN"], input[name*="pin"]')
            if pin_input and garena_pin:
                await pin_input.fill(garena_pin)
                logger.info("PIN entered")
                
                # Confirm PIN
                confirm_btn = await self.page.query_selector('button:has-text("Confirm"), button:has-text("OK"), button[type="submit"]')
                if confirm_btn:
                    await confirm_btn.click()
                    await asyncio.sleep(3)
            
            # Check for success message
            success_elem = await self.page.query_selector('.success, .alert-success, [class*="success"]')
            if success_elem:
                success_text = await success_elem.inner_text()
                logger.info(f"Purchase success: {success_text}")
                return True
            
            # Check for error
            error_elem = await self.page.query_selector('.error, .alert-danger, [class*="error"]')
            if error_elem:
                error_text = await error_elem.inner_text()
                logger.error(f"Purchase error: {error_text}")
                return False
            
            # Unclear result
            logger.warning("Purchase result unclear")
            return False
            
        except Exception as e:
            logger.error(f"Purchase completion error: {str(e)}")
            return False
    
    async def take_screenshot(self, filename: str):
        """Take a screenshot for debugging"""
        try:
            await self.page.screenshot(path=filename)
            logger.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"Screenshot error: {str(e)}")
    
    async def process_order(
        self,
        email: str,
        password: str,
        pin: str,
        player_uid: str,
        diamond_amount: int,
        server_region: str = "BD"
    ) -> Tuple[bool, str]:
        """
        Full automation flow for processing an order
        Returns (success, status_message)
        """
        try:
            # Step 1: Login
            if not await self.login(email, password):
                return False, "login_failed"
            
            # Step 2: Navigate to top-up page
            if not await self.navigate_to_topup(server_region):
                return False, "navigation_failed"
            
            # Step 3: Enter player UID
            if not await self.enter_player_uid(player_uid):
                return False, "uid_entry_failed"
            
            # Step 4: Validate player
            valid, player_name = await self.validate_player()
            if not valid:
                return False, "invalid_uid"
            
            # Step 5: Select package
            if not await self.select_package(diamond_amount):
                return False, "package_not_found"
            
            # Step 6: Complete purchase
            if not await self.complete_purchase(pin):
                return False, "purchase_failed"
            
            return True, "success"
            
        except Exception as e:
            logger.error(f"Order processing error: {str(e)}")
            return False, f"error: {str(e)}"


async def run_automation_for_order(
    order: dict,
    garena_email: str,
    garena_password: str,
    garena_pin: str,
    headless: bool = True
) -> Tuple[bool, str]:
    """
    Run automation for a single order
    Returns (success, status)
    """
    async with GarenaAutomation(headless=headless) as automation:
        success, status = await automation.process_order(
            email=garena_email,
            password=garena_password,
            pin=garena_pin,
            player_uid=order.get("player_uid"),
            diamond_amount=order.get("amount", 0),
            server_region="BD"  # Bangladesh server
        )
        
        # Take screenshot on failure for debugging
        if not success:
            screenshot_path = f"/tmp/automation_failure_{order.get('id', 'unknown')[:8]}.png"
            await automation.take_screenshot(screenshot_path)
            logger.info(f"Failure screenshot saved to {screenshot_path}")
        
        return success, status


# Example usage
if __name__ == "__main__":
    import sys
    
    async def test():
        test_order = {
            "id": "test-123",
            "player_uid": "12345678",
            "amount": 100,
        }
        
        # These would come from encrypted storage in production
        success, status = await run_automation_for_order(
            order=test_order,
            garena_email="test@example.com",
            garena_password="test123",
            garena_pin="1234",
            headless=False  # Show browser for testing
        )
        
        print(f"Result: success={success}, status={status}")
    
    asyncio.run(test())
