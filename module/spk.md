# Speech Synthesis Functionality Documentation

## 🛩️ Overview
This document describes the behavior of the speech synthesis functionality, focusing on how connections are managed, the auto-close mechanism, and expected logging outputs.

---

## 🛠️ Functional Behavior

| **Feature**                 | **Description**                                                                                                                 |
|-----------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| **Speech Synthesizer Initialization** | Creates a persistent connection to Azure's speech service to synthesize speech efficiently.                                     |
| **Auto-Close Timer** | A background task that monitors inactivity and closes the connection after 2 minutes of no speech synthesis requests.           |
| **Frequent Checks for Activity** | Every **30 seconds**, the system checks if a new synthesis request has been made.                                               |
| **Auto-Close Skipped Condition** | If a request is received before the timer expires, the connection remains open, and a log entry is created indicating the skip. |
| **Speech Synthesis Execution** | Converts text to speech using **Azure Cognitive Services**, keeping the connection alive while handling errors gracefully.      |
| **Connection Closure** | The connection is explicitly closed only when **no requests have been made for 2 minutes**.                                     |
| **Error Handling** | Detects synthesis failures and logs errors with details for debugging.                                                          |

---

## 🔍 Auto-Close Timer Behavior  

| **Scenario** | **Behavior** | **Expected Log Output**                                                                                                                                 |
|-------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| **First Request Arrives** | The connection is opened and the auto-close timer starts. | 🎧 Synthesizing text: *Hello there!* <br> ✅ Speech synthesis completed successfully. <br> ⏳ Auto-close timer started (2 min, checks every 30s).         |
| **10 seconds later (no new request)** | Timer checks for inactivity but does not close the connection yet. | 🔄 Auto-close skipped. Last request was **10.5 seconds ago**.                                                                                           |
| **Another request arrives before 2 min expires** | The timer resets and the connection remains open. | 🎧 Synthesizing text: *How are you?* <br> ✅ Speech synthesis completed successfully. <br> 🔄 Auto-close skipped. Last request was **90.2 seconds ago**. |
| **No requests for 2 minutes** | The connection is closed due to inactivity. | ⏳ No activity for 2 minutes. Closing connection. <br> 🚪 Closing connection due to inactivity. <br> ❌ Connection closed.                                |

---

## 🛠️ Connection Handling & Improvements
| **Problem** | **Solution**                                                       | **Impact** |
|------------|--------------------------------------------------------------------|------------|
| **Auto-close timer never runs due to blocking `sleep(120)`** | **Check every 30 seconds instead of waiting 2 minutes**.           | ✅ More frequent checks ensure the connection closes only when truly inactive. |
| **No log when auto-close is skipped** | **Added log message when a request arrives before timeout.**       | ✅ Helps track when the connection remains open due to activity. |
| **Speech synthesis blocking the event loop** | **Now runs non-blocking tasks using `asyncio.create_task()`**.     | ✅ Faster response time, better scalability for multiple users. |
| **Error handling lacked visibility** | **Detailed logs added for Azure errors and cancellation reasons.** | ✅ Easier debugging when synthesis fails. |

---

## 🔍 Summary of Key Fixes
✅ **Auto-close timer now checks every 30 seconds instead of waiting 2 minutes**  
✅ **Logs "🔄 Auto-close skipped" when a request arrives before timeout**  
✅ **Speech synthesis runs asynchronously, improving API performance**  
✅ **Detailed error handling ensures better debugging of speech synthesis failures**  
✅ **Connection closes only when truly inactive, optimizing resource usage**  

---

### 🚀 **Next Steps**
- **Test different request timings** to verify logs and connection behavior.
- **Monitor speech synthesis failures** and fine-tune error handling if needed.
- **Scale the solution for multiple concurrent users** using async optimizations.

---
