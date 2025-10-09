Ah! You're talking about the **API request body** - when we call the API, we're sending `payment_id` as the parameter name instead of using the actual attribute name from config!

---

## The Issue

When calling the API, we need to send the payment ID with the correct **JSON attribute name** from the config, not a hardcoded "payment_id".

**Example:**

Your config says:
```json
{
  "paymentIdMapping": {
    "mongoField": "mid",
    "jsonAttribute": "messageId"  // ← This is what the API expects!
  }
}
```

But we're probably sending:
```json
{
  "payment_id": "PAY001"  // ❌ Wrong - hardcoded
}
```

Should be:
```json
{
  "messageId": "PAY001"  // ✅ Correct - from config
}
```

---

## Where to Fix

### **1. In src/api_client.py - call_api method**

**Find this section where we build the request body:**

Look for something like:
```python
# Build request body
body = {
    'payment_id': payment_id  # ❌ HARDCODED!
}
```

**Change it to:**

```python
def call_api(
    self,
    payment_id: str,
    url_key: str,
    payment_id_attribute: str  # ← Add this parameter
) -> Dict[str, Any]:
    """
    Call API endpoint
    
    Args:
        payment_id: Payment ID value
        url_key: Which URL to use ('java21Url' or 'java8Url')
        payment_id_attribute: JSON attribute name for payment ID (from config)
    """
    # ...
    
    # Build request body with correct attribute name
    body = {
        payment_id_attribute: payment_id  # ✅ Use the config value
    }
```

---

### **2. In src/main.py - _test_single_payment_id method**

**Find where we call the API:**

Look for:
```python
# Step 2: Call Java 21 API
logger.debug("Calling Java 21 API...")
java21_response = self.api_client.call_api(
    payment_id=payment_id,
    url_key='java21Url'
)
```

**Change to:**

```python
# Step 2: Call Java 21 API
logger.debug("Calling Java 21 API...")

# Get payment ID attribute name from config
payment_id_attribute = self.test_config['paymentIdMapping']['jsonAttribute']

java21_response = self.api_client.call_api(
    payment_id=payment_id,
    url_key='java21Url',
    payment_id_attribute=payment_id_attribute  # ← Pass the attribute name
)
```

**And for Java 8:**

```python
# Step 3: Call Java 8 API if URL exists
java8_data = None
has_java8 = self.test_config.get('java8Url') is not None

if has_java8:
    logger.debug("Calling Java 8 API...")
    java8_response = self.api_client.call_api(
        payment_id=payment_id,
        url_key='java8Url',
        payment_id_attribute=payment_id_attribute  # ← Pass the attribute name
    )
```

---

## Summary of Changes

### **Change 1: src/api_client.py**

**In the `call_api` method signature:**
- Add parameter: `payment_id_attribute: str`

**In the request body building:**
- Change from: `body = {'payment_id': payment_id}`
- Change to: `body = {payment_id_attribute: payment_id}`

### **Change 2: src/main.py**

**In `_test_single_payment_id` method, before calling APIs:**
- Add this line:
  ```python
  payment_id_attribute = self.test_config['paymentIdMapping']['jsonAttribute']
  ```

**In both API calls (Java 21 and Java 8):**
- Add parameter: `payment_id_attribute=payment_id_attribute`

---

## Quick Check

After making these changes, add a debug log to verify:

**In src/api_client.py, in call_api method:**
```python
logger.debug(f"Building request body with attribute: {payment_id_attribute} = {payment_id}")
body = {payment_id_attribute: payment_id}
```

Run it and check the logs - you should see:
```
Building request body with attribute: messageId = PAY001
```

Instead of:
```
Building request body with attribute: payment_id = PAY001
```

---

That should fix it! The API will now receive the payment ID with the correct attribute name from your config. 🎯
