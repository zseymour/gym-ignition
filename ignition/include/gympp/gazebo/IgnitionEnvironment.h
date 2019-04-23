/*
 * Copyright (C) 2019 Istituto Italiano di Tecnologia (IIT)
 * All rights reserved.
 *
 * This software may be modified and distributed under the terms of the
 * GNU Lesser General Public License v2.1 or any later version.
 */

#ifndef GYMPP_GAZEBO_IGNITIONENVIRONMENT
#define GYMPP_GAZEBO_IGNITIONENVIRONMENT

#include "gympp/Environment.h"
#include "gympp/gazebo/GazeboWrapper.h"

#include <functional>
#include <memory>
#include <optional>
#include <vector>

namespace gympp {
    namespace gazebo {
        class IgnitionEnvironment;
        class EnvironmentCallbacks;
    } // namespace gazebo
} // namespace gympp

class gympp::gazebo::IgnitionEnvironment
    : public gympp::Environment
    , public gympp::gazebo::GazeboWrapper
    , public std::enable_shared_from_this<gympp::Environment>
{
private:
    class Impl;
    std::unique_ptr<Impl, std::function<void(Impl*)>> pImpl;
    gympp::gazebo::EnvironmentCallbacks* envCallbacks();

protected:
public:
    using Environment = gympp::Environment;
    using Environment::Action;
    using Environment::Observation;
    using Environment::RenderMode;
    using Environment::Reward;
    using Environment::State;

    IgnitionEnvironment() = delete;
    IgnitionEnvironment(const ActionSpacePtr aSpace,
                        const ObservationSpacePtr oSpace,
                        double updateRate,
                        uint64_t iterations);
    ~IgnitionEnvironment() override = default;

    bool render(RenderMode mode) override;
    std::optional<Observation> reset() override;
    std::optional<State> step(const Action& action) override;
    std::vector<size_t> seed(size_t seed = 0) override;

    EnvironmentPtr env();
};

#endif // GYMPP_GAZEBO_IGNITIONENVIRONMENT
