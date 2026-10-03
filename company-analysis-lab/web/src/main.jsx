import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App.jsx";

class Boundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="boot">
        <div className="boot-mark">AL</div>
        <p>Something went wrong while drawing this page: {String(this.state.error.message || this.state.error)}</p>
        <p className="small">Your saved work is not affected. Reload the page to continue.</p>
      </div>
    );
  }
}

createRoot(document.getElementById("root")).render(
  <Boundary>
    <App />
  </Boundary>,
);
