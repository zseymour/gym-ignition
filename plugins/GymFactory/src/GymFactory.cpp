/*
 * Copyright (C) 2019 Istituto Italiano di Tecnologia (IIT)
 * All rights reserved.
 *
 * This software may be modified and distributed under the terms of the
 * GNU Lesser General Public License v2.1 or any later version.
 */

#include "gympp/GymFactory.h"
#include "gympp/Log.h"
#include "gympp/Metadata.h"
#include "gympp/Space.h"
#include "gympp/gazebo/IgnitionEnvironment.h"

#include <cassert>
#include <ostream>
#include <unordered_map>

using namespace gympp;

class GymFactory::Impl
{
public:
    inline bool exists(const EnvironmentName& name) const
    {
        return plugins.find(name) != plugins.end();
    }
    spaces::SpacePtr makeSpace(const SpaceMetadata& md);
    std::unordered_map<EnvironmentName, const PluginMetadata> plugins;
};

gympp::spaces::SpacePtr gympp::GymFactory::Impl::makeSpace(const SpaceMetadata& md)
{
    assert(md.isValid());
    gympp::spaces::SpacePtr space;

    switch (md.type) {
        case gympp::SpaceType::Box: {
            if (md.dims.empty()) {
                space = std::make_shared<gympp::spaces::Box>(md.low, md.high);
            }
            else {
                space = std::make_shared<gympp::spaces::Box>(md.low[0], md.high[0], md.dims);
            }
            break;
        }
        case gympp::SpaceType::Discrete: {
            space = std::make_shared<gympp::spaces::Discrete>(md.dims[0]);
            break;
        }
    }

    return space;
}

gympp::GymFactory::GymFactory()
    : pImpl{new Impl(), [](Impl* impl) { delete impl; }}
{}

gympp::EnvironmentPtr gympp::GymFactory::make(const std::string& envName)
{
    if (!pImpl->exists(envName)) {
        gymppError << "Environment '" << envName << "' has never been registered" << std::endl;
        return nullptr;
    }

    auto& md = pImpl->plugins[envName];

    assert(md.isValid());
    auto actionSpace = pImpl->makeSpace(md.actionSpace);
    auto observationSpace = pImpl->makeSpace(md.observationSpace);

    if (!actionSpace || !observationSpace) {
        gymppError << "Failed to create spaces" << std::endl;
        return nullptr;
    }

    // Create the environment
    auto ignGym = std::make_shared<gazebo::IgnitionEnvironment>(actionSpace,
                                                                observationSpace,
                                                                /*updateRate=*/md.gazeboUpdateRate,
                                                                /*iterations=*/1);

    // Setup the world
    if (!ignGym->setupGazeboWorld(md.worldFileName)) {
        gymppError << "Failed to setup gazebo world";
        return nullptr;
    }

    // Setup the model
    if (!ignGym->setupGazeboModel(md.modelFileName)) {
        gymppError << "Failed to setup the gazebo model" << std::endl;
        return nullptr;
    }

    // Setup the plugin
    if (!ignGym->setupIgnitionPlugin(md.libraryName, md.className, md.environmentUpdateRate)) {
        gymppError << "Failed to setup the ignition plugin" << std::endl;
        return nullptr;
    }

    return ignGym->env();
}

bool gympp::GymFactory::registerPlugin(const PluginMetadata& md)
{
    if (!md.isValid()) {
        gymppError << "The plugin metadata is not valid" << std::endl;
        return false;
    }

    if (pImpl->exists(md.environmentName)) {
        gymppDebug << "Environment '" << md.environmentName << "' has been already registered"
                   << std::endl;
        return true;
    }

    pImpl->plugins.insert({md.environmentName, md});
    return true;
}