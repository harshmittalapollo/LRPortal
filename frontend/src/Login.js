import {useState} from "react"
import axios from "axios"

const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000"

function Login({ onLogin }){
  const [username,setUsername]=useState("")
  const [password,setPassword]=useState("")
  const [message,setMessage]=useState("")
  const [loading,setLoading]=useState(false)

  async function login(event){
    event.preventDefault()
    setLoading(true)
    setMessage("")

    try {
      const response = await axios.post(`${API_URL}/login`, {
        username,
        password,
      })

      if (response.data?.error) {
        setMessage(response.data.error)
        return
      }

      localStorage.setItem("token", response.data.token)

      if (typeof onLogin === "function") {
        onLogin({
          token: response.data.token,
          username: response.data.username,
          role: response.data.role,
        })
      }
    } catch (error) {
      console.error(error)
      setMessage("Unable to reach backend.Please confirm the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  return(
    <div>
      <h2>LR Portal</h2>
      {message && <p className="error">{message}</p>}
      <form onSubmit={login}>
        <input
          placeholder="Username"
          value={username}
          onChange={(e)=>setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e)=>setPassword(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
    </div>
  )
}

export default Login